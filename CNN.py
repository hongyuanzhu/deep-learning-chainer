# -*- coding: utf-8 -*-

import argparse
import time
import six
import six.moves.cPickle as pickle
import numpy as np
from sklearn.datasets import fetch_mldata
from sklearn.cross_validation import train_test_split
from chainer import cuda, Variable, FunctionSet, optimizers
import chainer.functions as F

class ConvolutionalNN:
	def __init__(self, data, target, in_channels=1,
									 n_hidden=100,
									 n_outputs=10,
									 gpu=-1):

		self.model = FunctionSet(conv1=	F.Convolution2D(in_channels, 32, 5),
								 conv2=	F.Convolution2D(32, 32, 5),
								 l3=	F.Linear(512, n_hidden),
								 l4=	F.Linear(n_hidden, n_outputs))

		if gpu >= 0:
			self.model.to_gpu()

		self.gpu = gpu

		self.x_train,\
		self.x_test,\
		self.y_train,\
		self.y_test = train_test_split(data, target, test_size=0.1)

		self.n_train = len(self.y_train)
		self.n_test = len(self.y_test)

		self.optimizer = optimizers.Adam()
		self.optimizer.setup(self.model.collect_parameters())

	def forward(self, x_data, y_data, train=True):

		if self.gpu >= 0:
			x_data = cuda.to_gpu(x_data)
			y_data = cuda.to_gpu(y_data)

		x, t = Variable(x_data), Variable(y_data)
		h = F.max_pooling_2d(F.relu(self.model.conv1(x)), ksize=2, stride=2)
		h = F.max_pooling_2d(F.relu(self.model.conv2(h)), ksize=3, stride=3)
		h = F.dropout(F.relu(self.model.l3(h)), train=train)
		y = self.model.l4(h)
		return F.softmax_cross_entropy(y, t), F.accuracy(y,t)

	def predict(self, x_data):

		if self.gpu >= 0:
			x_data = cuda.to_gpu(x_data)

		x = Variable(x_data)
		h = F.max_pooling_2d(F.relu(self.model.conv1(x)), ksize=2, stride=2)
		h = F.max_pooling_2d(F.relu(self.model.conv2(h)), ksize=3, stride=3)
		h = F.relu(self.model.l3(h))
		y = self.model.l4(h)
		s = F.softmax(y)
		return s.data

	def train_and_test(self, n_epoch=20, batchsize=100):
		for epoch in xrange(1, n_epoch+1):
			print 'epoch', epoch

			perm = np.random.permutation(self.n_train)
			sum_accuracy = 0
			sum_loss = 0
			for i in xrange(0, self.n_train, batchsize):
				x_batch = self.x_train[perm[i:i+batchsize]]
				y_batch = self.y_train[perm[i:i+batchsize]]

				real_batchsize = len(x_batch)

				self.optimizer.zero_grads()
				loss, acc = self.forward(x_batch, y_batch)
				loss.backward()
				self.optimizer.update()

				sum_loss += float(cuda.to_cpu(loss.data)) * real_batchsize
				sum_accuracy += float(cuda.to_cpu(acc.data)) * real_batchsize

			print 'train mean loss={}, accuracy={}'.format(sum_loss/self.n_train, sum_accuracy/self.n_train)

			# evalation
			sum_accuracy = 0
			sum_loss = 0
			for i in xrange(0, self.n_test, batchsize):
				x_batch = self.x_test[i:i+batchsize]
				y_batch = self.y_test[i:i+batchsize]

				real_batchsize = len(x_batch)

				loss, acc = self.forward(x_batch, y_batch, train=False)

				sum_loss += float(cuda.to_cpu(loss.data)) * real_batchsize
				sum_accuracy += float(cuda.to_cpu(acc.data)) * real_batchsize

			print 'test mean loss={}, accuracy={}'.format(sum_loss/self.n_test, sum_accuracy/self.n_test)

	def dump_model(self):
		self.model.to_cpu()
		pickle.dump(self.model, open('cnn_model', 'wb'), -1)

	def load_model(self):
		self.model = pickle.load(open('cnn_model','rb'))
		if self.gpu >= 0:
			self.model.to_gpu()
		self.optimizer.setup(self.model.collect_parameters())

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='MNIST')
	parser.add_argument('--gpu', '-g', default=-1, type=int,
						help='GPU ID (negative value indicates CPU)')
	args = parser.parse_args()

	if args.gpu >= 0:
		cuda.init(args.gpu)


	print 'fetch MNIST dataset'
	# mnist = fetch_mldata('MNIST original')
	# mnist.data   = mnist.data.astype(np.float32)
	# mnist.data  /= 255
	# mnist.data = mnist.data.reshape(70000,1,28,28)
	# mnist.target = mnist.target.astype(np.int32)
	# data = mnist.data
	# target = mnist.target
	# n_outputs = 10
	# in_channels = 1

	from animeface import AnimeFaceDataset
	print 'load AnimeFace dataset'
	dataset = AnimeFaceDataset()
	dataset.read_data_target()
	data = dataset.data
	target = dataset.target
	n_outputs = dataset.get_n_types_target()
	in_channels = 3


	start_time = time.time()

	cnn = ConvolutionalNN(data=data,
						  target=target,
						  gpu=args.gpu,
						  in_channels=in_channels,
						  n_outputs=n_outputs,
						  n_hidden=512)
	# cnn.train_and_test(n_epoch=10)
	# cnn.dump_model()

	cnn.load_model()

	while True:
		_input = raw_input()
		_input = _input[0:len(_input)-1]
		import cv2 as cv
		image = cv.imread(_input)
		image = cv.resize(image, (dataset.image_size, dataset.image_size))
		image = image.transpose(2,0,1)
		image = image/255.
		tmp = []
		tmp.append(image)
		data = np.array(tmp, np.float32)
		target = int(dataset.get_class_id(_input))
		predicted = cnn.predict(data)[0]
		rank = {}
		for i in xrange(len(predicted)):
			rank[dataset.index2name[i]] = predicted[i]
		rank = sorted(rank.items(),key=lambda x:x[1],reverse=True)
		for i in range(9):
			r = rank[i]
			print "#" + str(i+1) + '  ' + r[0] + '  ' + str(r[1]*100) + '%'
		print '#########################################'




	end_time = time.time()

	print "time = {} min".format((end_time-start_time)/60.0)









