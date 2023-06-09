import numpy as np
import vegans.utils as utils
import vegans.utils.loading as loading

from torch import nn
from vegans.GAN import WassersteinGAN, VanillaGAN
from vegans.utils.layers import LayerReshape


def call_gan_training(generator, adversary):
    gan_model = VanillaGAN(
        generator=generator, adversary=adversary,
        z_dim=z_dim, x_dim=im_dim, folder="./veganModels/GAN",
    )
    # gan_model.summary(save=True)
    gan_model.fit(
        X_train=X_train,
        X_test=X_test,
        batch_size=batch_size,
        epochs=epochs,
        steps={"Adversary": 5},
        print_every="0.5e",
        save_model_every=None,
        save_images_every="0.5e",
        save_losses_every=1,
        enable_tensorboard=True,
    )
    samples, losses = gan_model.get_training_results(by_epoch=False)
    utils.plot_images(images=samples.reshape(-1, *samples.shape[2:]), show=False)
    utils.plot_losses(losses=losses, show=True)

if __name__ == '__main__':

    loader = loading.MNISTLoader()
    X_train, y_train, X_test, y_test = loader.load()
    X_train = X_train[:500]
    epochs = 1
    batch_size = 64

    x_dim = X_train.shape[1:]

    #########################################################################
    # Convolutional network: Sequential
    #########################################################################
    z_dim = [1, 8, 8]
    generator = nn.Sequential(
        nn.ConvTranspose2d(in_channels=z_dim[0], out_channels=64, kernel_size=4, stride=2, padding=1),
        nn.LeakyReLU(0.2),
        nn.ConvTranspose2d(in_channels=64, out_channels=32, kernel_size=4, stride=2, padding=1),
        nn.LeakyReLU(0.2),
        nn.BatchNorm2d(32),
        nn.ConvTranspose2d(in_channels=32, out_channels=16, kernel_size=4, stride=2, padding=1),
        nn.LeakyReLU(0.2),
        nn.BatchNorm2d(16),
        nn.Conv2d(in_channels=16, out_channels=1, kernel_size=4, stride=2, padding=1),
        nn.Sigmoid()
    )

    adversary = nn.Sequential(
        nn.Conv2d(in_channels=x_dim[0], out_channels=32, kernel_size=4, stride=2, padding=1),
        nn.ReLU(),
        nn.Conv2d(in_channels=32, out_channels=8, kernel_size=4, stride=2, padding=1),
        nn.ReLU(),
        nn.Flatten(),
        nn.Linear(in_features=512, out_features=128),
        nn.ReLU(),
        nn.Linear(in_features=128, out_features=16),
        nn.ReLU(),
        nn.Linear(in_features=16, out_features=1),
        nn.Sigmoid()
    )
    z_dim = [1, 8, 8]
    call_gan_training(generator, adversary)


    #########################################################################
    # Convolutional network: OO
    #########################################################################
    z_dim = [1, 8, 8]

    class MyGenerator(nn.Module):
        def __init__(self, z_dim):
            super().__init__()
            self.hidden_part = nn.Sequential(
                nn.ConvTranspose2d(in_channels=z_dim[0], out_channels=64, kernel_size=4, stride=2, padding=1),
                nn.LeakyReLU(0.2),
                nn.ConvTranspose2d(in_channels=64, out_channels=32, kernel_size=4, stride=2, padding=1),
                nn.LeakyReLU(0.2),
                nn.BatchNorm2d(32),
                nn.ConvTranspose2d(in_channels=32, out_channels=16, kernel_size=4, stride=2, padding=1),
                nn.LeakyReLU(0.2),
                nn.BatchNorm2d(16),
                nn.Conv2d(in_channels=16, out_channels=1, kernel_size=4, stride=2, padding=1),
            )
            self.output = nn.Sigmoid()

        def forward(self, x):
            x = self.hidden_part(x)
            y_pred = self.output(x)
            return y_pred

    class MyAdversary(nn.Module):
        def __init__(self, x_dim):
            super().__init__()
            self.hidden_part = nn.Sequential(
                nn.Conv2d(in_channels=x_dim[0], out_channels=32, kernel_size=4, stride=2, padding=1),
                nn.ReLU(),
                nn.Conv2d(in_channels=32, out_channels=8, kernel_size=4, stride=2, padding=1),
                nn.ReLU(),
                nn.Flatten(),
                nn.Linear(in_features=512, out_features=128),
                nn.ReLU(),
                nn.Linear(in_features=128, out_features=16),
                nn.ReLU(),
                nn.Linear(in_features=16, out_features=1)
            )
            self.output = nn.Sigmoid()

        def forward(self, x):
            x = self.hidden_part(x)
            y_pred = self.output(x)
            return y_pred

    generator = MyGenerator(z_dim=z_dim)
    adversary = MyAdversary(x_dim=x_dim)
    call_gan_training(generator, adversary)


    #########################################################################
    # Flat network: Sequential
    #########################################################################
    z_dim = 2
    x_dim = X_train.shape[1:]

    generator = nn.Sequential(
        nn.Linear(z_dim, 128),
        nn.LeakyReLU(0.2),
        nn.Linear(128, 256),
        nn.LeakyReLU(0.2),
        nn.BatchNorm1d(256),
        nn.Linear(256, 512),
        nn.LeakyReLU(0.2),
        nn.BatchNorm1d(512),
        nn.Linear(512, 1024),
        nn.LeakyReLU(0.2),
        nn.BatchNorm1d(1024),
        nn.Linear(1024, int(np.prod(x_dim))),
        LayerReshape(x_dim),
        nn.Sigmoid()
    )
    adversary = nn.Sequential(
        nn.Flatten(),
        nn.Linear(int(np.prod(x_dim)), 512),
        nn.LeakyReLU(0.2),
        nn.Linear(512, 256),
        nn.LeakyReLU(0.2),
        nn.Linear(256, 1),
        nn.Sigmoid()
    )
    call_gan_training(generator, adversary)

    #########################################################################
    # Flat network: OO
    #########################################################################
    z_dim = 128

    class MyGenerator(nn.Module):
        def __init__(self, z_dim):
            super().__init__()
            self.hidden_part = nn.Sequential(
                nn.Linear(z_dim, 128),
                nn.LeakyReLU(0.2),
                nn.Linear(128, 256),
                nn.LeakyReLU(0.2),
                nn.BatchNorm1d(256),
                nn.Linear(256, 512),
                nn.LeakyReLU(0.2),
                nn.BatchNorm1d(512),
                nn.Linear(512, 1024),
                nn.LeakyReLU(0.2),
                nn.BatchNorm1d(1024),
                nn.Linear(1024, int(np.prod(x_dim))),
                LayerReshape(x_dim)
            )
            self.output = nn.Sigmoid()

        def forward(self, x):
            x = self.hidden_part(x)
            y_pred = self.output(x)
            return y_pred

    class MyAdversary(nn.Module):
        def __init__(self, x_dim):
            super().__init__()
            self.hidden_part = nn.Sequential(
                nn.Flatten(),
                nn.Linear(int(np.prod(x_dim)), 512),
                nn.LeakyReLU(0.2),
                nn.Linear(512, 256),
                nn.LeakyReLU(0.2),
                nn.Linear(256, 1)
            )
            self.output = nn.Sigmoid()

        def forward(self, x):
            x = self.hidden_part(x)
            y_pred = self.output(x)
            return y_pred

    generator = MyGenerator(z_dim=z_dim)
    adversary = MyAdversary(x_dim=x_dim)
    call_gan_training(generator, adversary)