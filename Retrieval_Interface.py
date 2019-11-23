# coding=utf-8
# /usr/bin/env pythpn

'''
Author: yinhao
Email: yinhao_x@163.com
Wechat: xss_yinhao
Github: http://github.com/yinhaoxs

data: 2019-09-18 14:05
desc:
'''

import argparse
import os
import time
import pickle
import pdb

import numpy as np

import torch
from torch.utils.model_zoo import load_url
from torchvision import transforms

from cirtorch.networks.imageretrievalnet import init_network, extract_vectors
from cirtorch.datasets.testdataset import configdataset
from cirtorch.utils.download import download_train, download_test
from cirtorch.utils.evaluate import compute_map_and_print
from cirtorch.utils.general import get_data_root, htime

# PRETRAINED = {
# 	'rSfM120k-tl-resnet50-gem-w': 'http://cmp.felk.cvut.cz/cnnimageretrieval/data/networks/retrieval-SfM-120k/rSfM120k-tl-resnet50-gem-w-97bf910.pth',
# 	'rSfM120k-tl-resnet101-gem-w': 'http://cmp.felk.cvut.cz/cnnimageretrieval/data/networks/retrieval-SfM-120k/rSfM120k-tl-resnet101-gem-w-a155e54.pth',
# 	'rSfM120k-tl-resnet152-gem-w': 'http://cmp.felk.cvut.cz/cnnimageretrieval/data/networks/retrieval-SfM-120k/rSfM120k-tl-resnet152-gem-w-f39cada.pth',
# 	'gl18-tl-resnet50-gem-w': 'http://cmp.felk.cvut.cz/cnnimageretrieval/data/networks/gl18/gl18-tl-resnet50-gem-w-83fdc30.pth',
# 	'gl18-tl-resnet101-gem-w': 'http://cmp.felk.cvut.cz/cnnimageretrieval/data/networks/gl18/gl18-tl-resnet101-gem-w-a4d43db.pth',
# 	'gl18-tl-resnet152-gem-w': 'http://cmp.felk.cvut.cz/cnnimageretrieval/data/networks/gl18/gl18-tl-resnet152-gem-w-21278d5.pth',
# }

# datasets_names = ['oxford5k', 'paris6k', 'roxford5k', 'rparis6k']

parser = argparse.ArgumentParser(description='PyTorch CNN Image Retrieval Testing End-to-End')

# test options
# parser.add_argument('--network', '-n', metavar='NETWORK',
# 					help="network to be evaluated: " +
# 						 " | ".join(PRETRAINED.keys()))
# parser.add_argument('--datasets', '-d', metavar='DATASETS', default='roxford5k,rparis6k',
# 					help="comma separated list of test datasets: " +
# 						 " | ".join(datasets_names) +
# 						 " (default: 'roxford5k,rparis6k')")
parser.add_argument('--image-size', '-imsize', default=(640, 480), type=int, metavar='N',
					help="maximum size of longer image side used for testing (default: 1024)")
parser.add_argument('--multiscale', '-ms', metavar='MULTISCALE', default='[1]',
					help="use multiscale vectors for testing, " +
						 " examples: '[1]' | '[1, 1/2**(1/2), 1/2]' | '[1, 2**(1/2), 1/2**(1/2)]' (default: '[1]')")

# GPU ID
parser.add_argument('--gpu-id', '-g', default='0', metavar='N',
					help="gpu id used for testing (default: '0')")


def main():
	args = parser.parse_args()

	# check if there are unknown datasets
	# for dataset in args.datasets.split(','):
	# 	if dataset not in datasets_names:
	# 		raise ValueError('Unsupported or unknown dataset: {}!'.format(dataset))

	# check if test dataset are downloaded
	# and download if they are not
	# download_train(get_data_root())
	# download_test(get_data_root())

	# setting up the visible GPU
	os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu_id

	# loading network
	# pretrained networks (downloaded automatically)
	print(">> Loading network:\n>>>> '{}'".format(args.network))
	# state = load_url(PRETRAINED[args.network], model_dir=os.path.join(get_data_root(), 'networks'))
	state = torch.load(args.network)
	# parsing net params from meta
	# architecture, pooling, mean, std required
	# the rest has default values, in case that is doesnt exist
	net_params = {}
	net_params['architecture'] = state['meta']['architecture']
	net_params['pooling'] = state['meta']['pooling']
	net_params['local_whitening'] = state['meta'].get('local_whitening', False)
	net_params['regional'] = state['meta'].get('regional', False)
	net_params['whitening'] = state['meta'].get('whitening', False)
	net_params['mean'] = state['meta']['mean']
	net_params['std'] = state['meta']['std']
	net_params['pretrained'] = False
	# network initialization
	net = init_network(net_params)
	net.load_state_dict(state['state_dict'])

	print(">>>> loaded network: ")
	print(net.meta_repr())

	# setting up the multi-scale parameters
	ms = list(eval(args.multiscale))
	print(">>>> Evaluating scales: {}".format(ms))

	# moving network to gpu and eval mode
	net.cuda()
	net.eval()

	# set up the transform
	normalize = transforms.Normalize(
		mean=net.meta['mean'],
		std=net.meta['std']
	)
	transform = transforms.Compose([
		transforms.ToTensor(),
		normalize
	])

	# evaluate on test datasets
	ukbeach = ""
	start = time.time()
	images, qimages = [], []
	for root, dirs, files in os.walk(ukbeach):
		for file in files:
			img_path = os.path.join(root+os.sep, file)
			images.append(img_path)
			qimages.append(img_path)

	# extract database and query vectors
	print('>> database images...')
	vecs = extract_vectors(net, images, args.image_size, transform, ms=ms)
	print('>> query images...')
	qvecs = extract_vectors(net, qimages, args.image_size, transform, ms=ms)

	print('>> Evaluating...')

	# convert to numpy
	vecs = vecs.numpy()
	qvecs = qvecs.numpy()

	# search, rank, and print
	scores = np.dot(vecs.T, qvecs)
	ranks = np.argsort(-scores, axis=0)

	print('>> elapsed time: {}'.format(htime(time.time() - start)))


if __name__ == '__main__':
	main()