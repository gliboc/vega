#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from glob import glob


from PIL import Image

from numpy import zeros, ones, array
from numpy.random import randint, normal

from keras.models import Sequential, Model
from keras.layers import (Activation, BatchNormalization, LeakyReLU,
                          Conv2D, Conv2DTranspose, Flatten, Input)
from keras.optimizers import Adam


CONFIG = {
    'size': 32,   # size of generated pictures
    'ngf': 16,    # number of G filters for the first conv layer
    'nx': 100,    # dimension for X
    'ny': 100,    # dimension for Y
    'nc': 3,      # number of output channels
    'ndf': 64,    # number of D filters for the first conv layer
    'lr': 0.0002, # initial learning rate for adam
    'beta1': 0.5, # momentum term for adam
    'alpha': 0.2, # LeakyReLU slope parameter
}

class CYCLEGAN:
    def __init__(self, cfg):
        self.img_shape = (cfg['size'], cfg['size'], cfg['nc'])
        self.nx = cfg['nx']
        self.ny = cfg['ny']
        self.ngf, self.ndf = cfg['ngf'], cfg['ndf']
        self.alpha = cfg['alpha']
        self.nc = cfg['nc']

        optimizer = Adam(lr=cfg['lr'], beta_1=cfg['beta1'])

        self.discr1 = self.build_discriminator()
        self.discr1.compile(loss='binary_crossentropy', optimizer=optimizer,
                           metrics=['accuracy'])
        self.discr1.trainable = False

        self.discr2 = self.build_discriminator()
        self.discr2.compile(loss='binary_crossentropy', optimizer=optimizer,
                           metrics=['accuracy'])
        self.discr2.trainable = False

        self.gen1 = self.build_generator()

        self.gen2 = self.build_generator()


        x = Input(shape=self.img_shape)
        y = Input(shape=self.img_shape)
        self.first_gen = self.discr1(self.gen1(x))
        self.second_gen = self.discr2(self.gen2(y))

        #self.m1_gen= Model(y, self.gen1(x))
        #self.m1_gen.compile(loss='mean_squared_error', optimizer=optimizer)

        self.comb1 = Model(x, self.first_gen)

        self.comb2 = Model(y, self.second_gen)

        self.comb = Model(x, (self.gen2(self.gen1(x))))

        #self.comb = Model(z, self.discr(self.gen(z)))
        self.comb.compile(loss='mean_absolute_error', optimizer=optimizer)

        self.comb.summary()

    def train(self, epochs, half_batch, save_interval):
        # TODO: load images
        x_train = self.load_images()

        for epoch in range(epochs):
            ## Discriminator
            real = x_train[randint(0, x_train.shape[0], half_batch)]
            d_loss_r = self.discr1.train_on_batch(real, ones((half_batch, 1)))

            z = normal(0, 1, (half_batch, self.nz))
            fake = self.gen1.predict(z)
            d_loss_f = self.discr1.train_on_batch(fake, zeros((half_batch, 1)))

            d_loss = .5*(d_loss_r + d_loss_f)

            ## Generator
            z = normal(0, 1, (2 * half_batch, self.nz))
            g_loss = self.comb.train_on_batch(z, ones((2 * half_batch, 1)))

            print('[%04i] [D loss: %.3f, acc: %.2f%%] [G loss: %.3f]' %
                  (epoch, d_loss[0], 100*d_loss[1], g_loss))

            if epoch % save_interval == 0:
                self.save_images(epoch)

    def load_images(self):
        xs = []

        for path in glob('input/*.png'):
            img = array(Image.open(path))
            if img.shape == self.img_shape:
                xs.append(img)
            else:
                print('bad shape for %s: %s' % (path, img.shape))

        return array(xs)

    def save_images(self, epoch, n=(5, 5)):
        imgs = self.gen.predict(normal(0, 1, (n[0] * n[1], self.nz)))

        # size of a tile
        s0 = self.img_shape[0] + 2
        s1 = self.img_shape[1] + 2

        out = Image.new('rgb', (2 + n[0]*s0, 2 + n[1]*s1))

        for i in range(n[0]):
            for j in range(n[1]):
                out.paste(Image.fromarray(imgs[n[1]*i + j,:,:,:], mode='rgb'),
                          (2 + s0*i, 2 + s1*j))

        out.save('output/dcgan_%04i.png')

    def build_generator(self):
        """Create the generator model as described in the paper."""

        model = Sequential()

        model.add(Conv2D(filters=self.ngf, kernel_size=4, input_shape=self.img_shape))
        model.add(Activation('relu'))
        model.add(BatchNormalization())

        model.add(Conv2D(filters=self.ngf * 4, kernel_size=4))
        model.add(Activation('relu'))
        model.add(BatchNormalization())

        #model.add(Conv2DTranspose(filters=self.ngf * 2, kernel_size=4,
        #                          strides=2, padding='same'))
        #model.add(Activation('relu'))
        #model.add(BatchNormalization())

        model.add(Conv2DTranspose(filters=self.ngf, kernel_size=4))
        model.add(Activation('relu'))
        model.add(BatchNormalization())

        model.add(Conv2DTranspose(filters=self.ngf, kernel_size=3))
        model.add(Conv2DTranspose(filters=self.img_shape[2], kernel_size=2,
                                  activation='tanh'))

        print('\n%%% Generator %%%')
        model.summary()

        return model

    def build_discriminator(self):
        """Create the discriminator model as described in the paper."""

        model = Sequential()

        model.add(Conv2D(filters=self.ndf, kernel_size=4, padding='same',
                         strides=2, input_shape=self.img_shape))
        model.add(LeakyReLU(self.alpha))

        #model.add(Conv2D(filters=self.ndf * 2, kernel_size=4, padding='same',
        #                 strides=2))
        #model.add(LeakyReLU(self.alpha))
        #model.add(BatchNormalization())

        model.add(Conv2D(filters=self.ndf, kernel_size=4, padding='same',
                         strides=2))
        model.add(LeakyReLU(self.alpha))
        model.add(BatchNormalization())

        model.add(Conv2D(filters=self.ndf * 8, kernel_size=4, padding='same',
                         strides=2))
        model.add(LeakyReLU(self.alpha))
        model.add(BatchNormalization())

        model.add(Conv2D(filters=1, kernel_size=4, activation='sigmoid'))
        model.add(Flatten())

        print('\n%%% Discriminator %%%')
        model.summary()

        return model

d = CYCLEGAN(CONFIG)
