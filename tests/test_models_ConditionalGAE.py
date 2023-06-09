"""
Test for conditional models with encoder, generator, adversary structure.
"""

import torch
import pytest

import numpy as np

from vegans.GAN import ConditionalAAE, ConditionalBicycleGAN, ConditionalLRGAN, ConditionalVAEGAN
from vegans.utils import get_input_dim
from vegans.utils.layers import LayerReshape

networks_flat = [
    (ConditionalAAE, 15, 10),
    (ConditionalBicycleGAN, 21, 10+1),
    (ConditionalLRGAN, 21, 10),
    (ConditionalVAEGAN, 21, 10+1),
]
networks_image = [
    (ConditionalAAE, 15, 10),
    (ConditionalBicycleGAN, [8, 16, 16], 10+1),
    (ConditionalLRGAN, [8, 16, 16], 10),
    (ConditionalVAEGAN, [8, 16, 16], 10+1),
]

def generate_net(in_dim, last_layer, out_dim):
    class MyNetwork(torch.nn.Module):
        def __init__(self, in_dim, last_layer, out_dim):
            super().__init__()
            in_dim = np.prod(in_dim)
            out_dim = [out_dim] if isinstance(out_dim, int) else out_dim
            self.hidden_part = torch.nn.Sequential(
                torch.nn.Flatten(),
                torch.nn.Linear(in_dim, 16),
                torch.nn.LeakyReLU(0.2),
                torch.nn.Linear(16, np.prod(out_dim)),
                LayerReshape(out_dim)

            )
            self.output = last_layer()

        def forward(self, x):
            x = self.hidden_part(x)
            return self.output(x)

    return MyNetwork(in_dim, last_layer, out_dim)


@pytest.mark.parametrize("gan, adv_dim, enc_dim", networks_flat)
def test_init(gan, adv_dim, enc_dim):
    z_dim = 10
    x_dim = 16
    y_dim = 5

    gen = generate_net(in_dim=z_dim+y_dim, last_layer=torch.nn.Sigmoid, out_dim=x_dim)
    enc = generate_net(in_dim=x_dim+y_dim, last_layer=torch.nn.Identity, out_dim=enc_dim)

    # TEST CRITIC
    crit = generate_net(in_dim=adv_dim, last_layer=torch.nn.Identity, out_dim=1)
    testgan = gan(generator=gen, adversary=crit, encoder=enc, x_dim=x_dim, z_dim=z_dim, y_dim=y_dim, adv_type="Critic", folder=None)

    # TEST DISCRIMINATOR
    disc = generate_net(in_dim=adv_dim, last_layer=torch.nn.Sigmoid, out_dim=1)
    testgan = gan(generator=gen, adversary=disc, encoder=enc, x_dim=x_dim, z_dim=z_dim, y_dim=y_dim, folder=None)

    # TEST x_dim AND z_dim
    with pytest.raises(TypeError):
        gan(generator=gen, adversary=disc, encoder=enc, x_dim=17, z_dim=10, folder=None)
    with pytest.raises(TypeError):
        gan(generator=gen, adversary=disc, encoder=enc, x_dim=16, z_dim=11, folder=None)

    # TEST GENERATOR OUTPUT DIMENSIONS
    gen = generate_net(in_dim=z_dim+y_dim, last_layer=torch.nn.Sigmoid, out_dim=17)
    with pytest.raises(AssertionError):
        gan(generator=gen, adversary=disc, encoder=enc, x_dim=16, z_dim=10, y_dim=y_dim, folder=None)

    # TEST ENCODER OUTPUT DIMENSIONS
    if enc_dim == z_dim:
        gen = generate_net(in_dim=z_dim+y_dim, last_layer=torch.nn.Sigmoid, out_dim=16)
        enc = generate_net(in_dim=x_dim+y_dim, last_layer=torch.nn.Identity, out_dim=17)
        with pytest.raises(AssertionError):
            gan(generator=gen, adversary=disc, encoder=enc, x_dim=16, z_dim=10, y_dim=y_dim, folder=None)


@pytest.mark.parametrize("gan, adv_dim, enc_dim", networks_flat)
def test_fit_vector(gan, adv_dim, enc_dim):
    z_dim = 10
    x_dim = 16
    y_dim = 5

    X_train = np.zeros(shape=[100, x_dim])
    y_train = np.zeros(shape=[100, y_dim])
    X_test = np.zeros(shape=[100, x_dim])
    y_test = np.zeros(shape=[100, y_dim])

    gen = generate_net(in_dim=z_dim+y_dim, last_layer=torch.nn.Sigmoid, out_dim=x_dim)
    enc = generate_net(in_dim=x_dim+y_dim, last_layer=torch.nn.Identity, out_dim=enc_dim)
    fit_kwargs = {
        "epochs": 1, "batch_size": 4, "steps": None, "print_every": None, "save_model_every": None,
        "save_images_every": None, "save_losses_every": "1e", "enable_tensorboard": False
    }

    # TEST CRITIC
    crit = generate_net(in_dim=adv_dim, last_layer=torch.nn.Identity, out_dim=1)
    testgan = gan(generator=gen, adversary=crit, encoder=enc, x_dim=x_dim, z_dim=z_dim, y_dim=y_dim, adv_type="Critic", folder=None)
    testgan.fit(
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test, **fit_kwargs
    )
    assert hasattr(testgan, "logged_losses")

    # TEST DISCRIMINATOR
    disc = generate_net(in_dim=adv_dim, last_layer=torch.nn.Sigmoid, out_dim=1)
    testgan = gan(generator=gen, adversary=disc, encoder=enc, x_dim=x_dim, z_dim=z_dim, y_dim=y_dim, folder=None)
    testgan.fit(
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test, **fit_kwargs
    )
    assert hasattr(testgan, "logged_losses")


@pytest.mark.parametrize("gan, adv_dim, enc_dim", networks_flat)
def test_fit_vector_feature_loss(gan, adv_dim, enc_dim):
    z_dim = 10
    x_dim = 16
    y_dim = 5

    X_train = np.zeros(shape=[100, x_dim])
    y_train = np.zeros(shape=[100, y_dim])
    X_test = np.zeros(shape=[100, x_dim])
    y_test = np.zeros(shape=[100, y_dim])

    gen = generate_net(in_dim=z_dim+y_dim, last_layer=torch.nn.Sigmoid, out_dim=x_dim)
    enc = generate_net(in_dim=x_dim+y_dim, last_layer=torch.nn.Identity, out_dim=enc_dim)
    fit_kwargs = {
        "epochs": 1, "batch_size": 4, "steps": None, "print_every": None, "save_model_every": None,
        "save_images_every": None, "save_losses_every": "1e", "enable_tensorboard": False
    }

    # TEST CRITIC
    crit = generate_net(in_dim=adv_dim, last_layer=torch.nn.Identity, out_dim=1)
    testgan = gan(
        generator=gen, adversary=crit, encoder=enc, x_dim=x_dim, z_dim=z_dim, y_dim=y_dim,
        folder=None, adv_type="Critic", feature_layer=crit.hidden_part
    )
    testgan.fit(
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test, **fit_kwargs
    )
    assert hasattr(testgan, "logged_losses")

    # TEST DISCRIMINATOR
    disc = generate_net(in_dim=adv_dim, last_layer=torch.nn.Sigmoid, out_dim=1)
    testgan = gan(
        generator=gen, adversary=disc, encoder=enc, x_dim=x_dim, z_dim=z_dim, y_dim=y_dim,
        folder=None, feature_layer=disc.hidden_part
    )
    testgan.fit(
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test, **fit_kwargs
    )
    assert hasattr(testgan, "logged_losses")


@pytest.mark.parametrize("gan, adv_dim, enc_dim", networks_flat)
def test_fit_error_vector(gan, adv_dim, enc_dim):
    z_dim = 10
    x_dim = 16
    y_dim = 5

    X_train = np.zeros(shape=[100, x_dim])
    X_train_wrong_shape1 = np.zeros(shape=[100])
    X_train_wrong_shape2 = np.zeros(shape=[100, x_dim+1])
    X_train_wrong_shape3 = np.zeros(shape=[100, 17, 14])
    X_train_wrong_shape4 = np.zeros(shape=[100, 17, 10, 10])
    X_test_wrong_shape = np.zeros(shape=[100, 17])

    y_train = np.zeros(shape=[100, y_dim])
    y_test = np.zeros(shape=[100, y_dim])

    gen = generate_net(in_dim=z_dim+y_dim, last_layer=torch.nn.Sigmoid, out_dim=x_dim)
    enc = generate_net(in_dim=x_dim+y_dim, last_layer=torch.nn.Identity, out_dim=enc_dim)
    disc = generate_net(in_dim=adv_dim, last_layer=torch.nn.Sigmoid, out_dim=1)
    fit_kwargs = {
        "epochs": 1, "batch_size": 4, "steps": None, "print_every": None, "save_model_every": None,
        "save_images_every": None, "save_losses_every": "1e", "enable_tensorboard": False
    }

    testgan = gan(
        generator=gen, adversary=disc, encoder=enc, x_dim=x_dim, z_dim=z_dim, y_dim=y_dim,
        folder=None, feature_layer=disc.hidden_part
    )

    with pytest.raises(AssertionError):
        testgan.fit(
            X_train=X_train_wrong_shape1, y_train=y_train, **fit_kwargs
        )

    with pytest.raises(AssertionError):
        testgan.fit(
            X_train=X_train_wrong_shape2, y_train=y_train, **fit_kwargs
        )

    with pytest.raises(AssertionError):
        testgan.fit(
            X_train=X_train_wrong_shape3, y_train=y_train, **fit_kwargs
        )

    with pytest.raises(AssertionError):
        testgan.fit(
            X_train=X_train_wrong_shape4, y_train=y_train, **fit_kwargs
        )

    with pytest.raises(AssertionError):
        testgan.fit(
            X_train=X_train, y_train=y_train, X_test=X_test_wrong_shape, y_test=y_test, **fit_kwargs
        )


@pytest.mark.parametrize("gan, adv_dim, enc_dim", networks_image)
def test_fit_image(gan, adv_dim, enc_dim):
    z_dim = 10
    x_dim = [3, 16, 16]
    y_dim = 5

    X_train = np.zeros(shape=[100, *x_dim])
    y_train = np.zeros(shape=[100, y_dim])
    X_test = np.zeros(shape=[100, *x_dim])
    y_test = np.zeros(shape=[100, y_dim])

    gen = generate_net(in_dim=z_dim+y_dim, last_layer=torch.nn.Sigmoid, out_dim=x_dim)
    enc = generate_net(in_dim=get_input_dim(x_dim, y_dim), last_layer=torch.nn.Identity, out_dim=enc_dim)
    disc = generate_net(in_dim=adv_dim, last_layer=torch.nn.Sigmoid, out_dim=1)
    fit_kwargs = {
        "epochs": 1, "batch_size": 4, "steps": None, "print_every": None, "save_model_every": None,
        "save_images_every": None, "save_losses_every": "1e", "enable_tensorboard": False
    }

    testgan = gan(
        generator=gen, adversary=disc, encoder=enc, x_dim=x_dim, z_dim=z_dim, y_dim=y_dim,
        folder=None
    )
    testgan.fit(
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test, **fit_kwargs
    )
    assert hasattr(testgan, "logged_losses")


@pytest.mark.parametrize("gan, adv_dim, enc_dim", networks_image)
def test_fit_image_feature_loss(gan, adv_dim, enc_dim):
    z_dim = 10
    x_dim = [3, 16, 16]
    y_dim = 5

    X_train = np.zeros(shape=[100, *x_dim])
    y_train = np.zeros(shape=[100, y_dim])
    X_test = np.zeros(shape=[100, *x_dim])
    y_test = np.zeros(shape=[100, y_dim])

    gen = generate_net(in_dim=z_dim+y_dim, last_layer=torch.nn.Sigmoid, out_dim=x_dim)
    enc = generate_net(in_dim=get_input_dim(x_dim, y_dim), last_layer=torch.nn.Identity, out_dim=enc_dim)
    disc = generate_net(in_dim=adv_dim, last_layer=torch.nn.Sigmoid, out_dim=1)
    fit_kwargs = {
        "epochs": 1, "batch_size": 4, "steps": None, "print_every": None, "save_model_every": None,
        "save_images_every": None, "save_losses_every": "1e", "enable_tensorboard": False
    }

    testgan = gan(
        generator=gen, adversary=disc, encoder=enc, x_dim=x_dim, z_dim=z_dim, y_dim=y_dim,
        folder=None, feature_layer=disc.hidden_part
    )
    testgan.fit(
        X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test, **fit_kwargs
    )
    assert hasattr(testgan, "logged_losses")


@pytest.mark.parametrize("gan, adv_dim, enc_dim", networks_image)
def test_fit_image_error(gan, adv_dim, enc_dim):
    z_dim = 10
    x_dim = [3, 16, 16]
    y_dim = 5

    X_train = np.zeros(shape=[100, *x_dim])
    X_train_wrong_shape1 = np.zeros(shape=[100])
    X_train_wrong_shape2 = np.zeros(shape=[100, 17])
    X_train_wrong_shape3 = np.zeros(shape=[100, 17, 14])
    X_train_wrong_shape4 = np.zeros(shape=[100, 4, 16, 16])
    X_test_wrong_shape = np.zeros(shape=[100, 3, 17, 17])

    y_train = np.zeros(shape=[100, y_dim])
    y_test = np.zeros(shape=[100, y_dim])

    gen = generate_net(in_dim=z_dim+y_dim, last_layer=torch.nn.Sigmoid, out_dim=x_dim)
    enc = generate_net(in_dim=get_input_dim(x_dim, y_dim), last_layer=torch.nn.Identity, out_dim=enc_dim)
    disc = generate_net(in_dim=adv_dim, last_layer=torch.nn.Sigmoid, out_dim=1)
    fit_kwargs = {
        "epochs": 1, "batch_size": 4, "steps": None, "print_every": None, "save_model_every": None,
        "save_images_every": None, "save_losses_every": "1e", "enable_tensorboard": False
    }

    testgan = gan(
        generator=gen, adversary=disc, encoder=enc, x_dim=x_dim, z_dim=z_dim, y_dim=y_dim,
        folder=None, feature_layer=disc.hidden_part
    )
    with pytest.raises(AssertionError):
        testgan.fit(
            X_train=X_train_wrong_shape1, y_train=y_train, **fit_kwargs
        )

    with pytest.raises(AssertionError):
        testgan.fit(
            X_train=X_train_wrong_shape2, y_train=y_train, **fit_kwargs
        )

    with pytest.raises(AssertionError):
        testgan.fit(
            X_train=X_train_wrong_shape3, y_train=y_train, **fit_kwargs
        )

    with pytest.raises(AssertionError):
        testgan.fit(
            X_train=X_train_wrong_shape4, y_train=y_train, **fit_kwargs
        )

    with pytest.raises(AssertionError):
        testgan.fit(
            X_train=X_train, y_train=y_train, X_test=X_test_wrong_shape, y_test=y_test, **fit_kwargs
        )

    with pytest.raises(AssertionError):
        testgan = gan(
            generator=gen, adversary=disc, encoder=enc, x_dim=x_dim, z_dim=z_dim, y_dim=y_dim,
            folder=None, feature_layer="hidden_part"
        )

@pytest.mark.parametrize("gan, optim", [
    (ConditionalAAE, torch.optim.Adam),
    (ConditionalBicycleGAN, torch.optim.Adam),
    (ConditionalLRGAN, torch.optim.Adam),
    (ConditionalVAEGAN, torch.optim.Adam),
    ]
)
def test_default_optimizers(gan, optim):
    assert gan._default_optimizer(gan) == optim
