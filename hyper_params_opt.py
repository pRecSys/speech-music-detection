import numpy as np

from hyperopt import Trials, STATUS_OK, tpe
from hyperas import optim
from hyperas.distributions import choice, uniform, conditional

from smd.models import tcn, b_lstm, b_conv_lstm
import smd.config as config
import smd.utils as utils
from smd.data.data_generator import DataGenerator
from smd.data.dataset_loader import DatasetLoader
from smd.data.data_augmentation import random_loudness_spec, random_filter_spec, block_mixing_spec, pitch_time_deformation_spec
from smd.data import preprocessing

from keras import optimizers


def data():
    cfg = {"dataset": ["ofai"],
           "data_location": "/Users/quentin/Computer/DataSet/Music/speech_music_detection/",
           "target_seq_length": 270,
           "batch_size": 32
           }

    def training_data_processing(spec_file, annotation_file, mean, std, spec_file2=None, annotation_file2=None):
        spec = np.load(spec_file)
        spec, stretching_rate = pitch_time_deformation_spec(spec)
        spec = random_filter_spec(spec)
        spec = random_loudness_spec(spec)
        label = preprocessing.get_label(
            annotation_file, spec.shape[1], stretching_rate=stretching_rate)

        if not(spec_file2 is None):
            spec2 = np.load(spec_file2)
            spec2, stretching_rate2 = pitch_time_deformation_spec(spec2)
            spec2 = random_filter_spec(spec2)
            spec2 = random_loudness_spec(spec2)
            label2 = preprocessing.get_label(
                annotation_file2, spec2.shape[1], stretching_rate=stretching_rate2)
            spec, label = block_mixing_spec(spec, spec2, label, label2)

        mels = preprocessing.get_scaled_mel_bands(spec)
        mels = preprocessing.normalize(mels, mean, std)
        return mels, label

    def validation_data_processing(spec_file, annotation_file, mean, std):
        spec = np.load(spec_file)

        mels = preprocessing.get_scaled_mel_bands(spec)
        mels = preprocessing.normalize(mels, mean, std)
        n_frame = mels.shape[1]
        label = preprocessing.get_label(
            annotation_file, n_frame, stretching_rate=1)
        return mels, label

    datasets_config = utils.load_json("datasets.json")
    dataset = DatasetLoader(
        cfg["dataset"], cfg["data_location"], datasets_config)

    train_set = DataGenerator(dataset.get_train_set(),
                              cfg["batch_size"],
                              cfg["target_seq_length"],
                              training_data_processing,
                              dataset.get_training_mean(),
                              dataset.get_training_std(),
                              set_type="train")

    val_set = DataGenerator(dataset.get_val_set(),
                            cfg["batch_size"],
                            cfg["target_seq_length"],
                            validation_data_processing,
                            dataset.get_training_mean(),
                            dataset.get_training_std(),
                            set_type="val")
    return train_set, val_set


def fit_b_lstm(train_set, val_set):
    cfg = {"optimizer":
           {
               "name": "SGD",
               "lr": 0.001,
               "momentum": 0.9,
               "decay": 0
           },
           "batch_size": 32,
           "workers": 8,
           "use_multiprocessing": True,
           "n_epochs": 5,
           "max_params": 1000000
           }
    n_layer = {{choice([2, 3, 4, 5])}}
    layers = []

    layers.append(
        {{choice([25, 50, 75, 100, 125, 150, 175, 200, 225, 250])}})
    if conditional(n_layer) == 2:
        layers.append(
            {{choice([25, 50, 75, 100, 125, 150, 175, 200, 225, 250])}})
    elif conditional(n_layer) == 3:
        layers.append(
            {{choice([25, 50, 75, 100, 125, 150, 175, 200, 225, 250])}})
        layers.append(
            {{choice([25, 50, 75, 100, 125, 150, 175, 200, 225, 250])}})
    elif conditional(n_layer) == 4:
        layers.append(
            {{choice([25, 50, 75, 100, 125, 150, 175, 200, 225, 250])}})
        layers.append(
            {{choice([25, 50, 75, 100, 125, 150, 175, 200, 225, 250])}})
        layers.append(
            {{choice([25, 50, 75, 100, 125, 150, 175, 200, 225, 250])}})
    elif conditional(n_layer) == 5:
        layers.append(
            {{choice([25, 50, 75, 100, 125, 150, 175, 200, 225, 250])}})
        layers.append(
            {{choice([25, 50, 75, 100, 125, 150, 175, 200, 225, 250])}})
        layers.append(
            {{choice([25, 50, 75, 100, 125, 150, 175, 200, 225, 250])}})
        layers.append(
            {{choice([25, 50, 75, 100, 125, 150, 175, 200, 225, 250])}})

    model = b_lstm.create_b_lstm(
        hidden_units=layers, dropout={{uniform(0.05, 0.5)}})

    n_params = model.count_params()
    print("n_params: " + str(n_params))
    if n_params > cfg["max_params"]:
        print("Too much parameters")
        return {'loss': np.inf, 'status': STATUS_OK, 'model': model}

    optimizer = optimizers.SGD(
        lr=cfg["optimizer"]["lr"], momentum=cfg["optimizer"]["momentum"], decay=cfg["optimizer"]["decay"])

    model.compile(loss=config.LOSS, metrics=config.METRICS,
                  optimizer=optimizer)

    result = model.fit_generator(train_set,
                                 epochs=cfg["n_epochs"],
                                 validation_data=val_set,
                                 workers=cfg["workers"],
                                 use_multiprocessing=cfg["use_multiprocessing"],
                                 shuffle=True
                                 )

    validation_loss = np.amin(result.history['val_loss'])
    print('Best validation acc of epoch:', validation_loss)
    return {'loss': validation_loss, 'status': STATUS_OK, 'model': model}


def fit_b_conv_lstm(train_set, val_set):
    cfg = {"optimizer":
           {
               "name": "SGD",
               "lr": 0.001,
               "momentum": 0.9,
               "decay": 0
           },
           "batch_size": 32,
           "workers": 8,
           "use_multiprocessing": True,
           "n_epochs": 5,
           "max_params": 1000000
           }
    n_layer = {{choice([2, 3, 4, 5])}}
    filters_list = []
    kernel_size_list = []
    stride_list = []
    dilation_rate_list = []

    filters_list.append({{choice([16, 32, 64])}})
    filters_list.append({{choice([16, 32, 64])}})
    kernel_size_list.append({{choice([1, 3, 5])}})
    kernel_size_list.append({{choice([1, 3, 5])}})
    stride_list.append(1)
    stride_list.append(1)
    dilation_rate_list.append(1)
    dilation_rate_list.append(1)
    if conditional(n_layer) == 3:
        filters_list.append({{choice([16, 32, 64])}})
        kernel_size_list.append({{choice([1, 3, 5])}})
        stride_list.append(1)
        dilation_rate_list.append(1)
    elif conditional(n_layer) == 4:
        filters_list.append({{choice([16, 32, 64])}})
        filters_list.append({{choice([16, 32, 64])}})
        kernel_size_list.append({{choice([1, 3, 5])}})
        kernel_size_list.append({{choice([1, 3, 5])}})
        stride_list.append(1)
        stride_list.append(1)
        dilation_rate_list.append(1)
        dilation_rate_list.append(1)
    elif conditional(n_layer) == 5:
        filters_list.append({{choice([16, 32, 64])}})
        filters_list.append({{choice([16, 32, 64])}})
        filters_list.append({{choice([16, 32, 64])}})
        kernel_size_list.append({{choice([1, 3, 5])}})
        kernel_size_list.append({{choice([1, 3, 5])}})
        kernel_size_list.append({{choice([1, 3, 5])}})
        stride_list.append(1)
        stride_list.append(1)
        dilation_rate_list.append(1)
        dilation_rate_list.append(1)
        stride_list.append(1)
        dilation_rate_list.append(1)

    model = b_conv_lstm.create_b_conv_lstm(filters_list=filters_list,
                                           kernel_size_list=kernel_size_list,
                                           stride_list=stride_list,
                                           dilation_rate_list=dilation_rate_list,
                                           dropout={{uniform(0.05, 0.5)}})
    n_params = model.count_params()
    print("n_params: " + str(n_params))
    if n_params > cfg["max_params"]:
        print("Too much parameters")
        return {'loss': np.inf, 'status': STATUS_OK, 'model': model}

    optimizer = optimizers.SGD(
        lr=cfg["optimizer"]["lr"], momentum=cfg["optimizer"]["momentum"], decay=cfg["optimizer"]["decay"])

    model.compile(loss=config.LOSS, metrics=config.METRICS,
                  optimizer=optimizer)

    result = model.fit_generator(train_set,
                                 epochs=cfg["n_epochs"],
                                 validation_data=val_set,
                                 workers=cfg["workers"],
                                 use_multiprocessing=cfg["use_multiprocessing"],
                                 shuffle=True
                                 )

    validation_loss = np.amin(result.history['val_loss'])
    print('Best validation acc of epoch:', validation_loss)
    return {'loss': validation_loss, 'status': STATUS_OK, 'model': model}


def fit_tcn(train_set, val_set):
    cfg = {"optimizer":
           {
               "name": "SGD",
               "lr": 0.001,
               "momentum": 0.9,
               "decay": 0
           },
           "batch_size": 32,
           "workers": 8,
           "use_multiprocessing": True,
           "n_epochs": 5,
           "max_params": 1000000
           }
    nb_filters = []
    kernel_size = {{choice([3, 5, 7, 9, 11, 13, 15, 17, 19])}}
    dilations = {{choice([[2 ** i for i in range(4)],
                          [2 ** i for i in range(5)],
                          [2 ** i for i in range(6)],
                          [2 ** i for i in range(7)],
                          [2 ** i for i in range(8)]])}}
    nb_stacks = {{choice([3, 4, 5, 6, 7, 8, 9, 10])}}
    use_skip_connections = {{choice([True, False])}}
    n_layers = {{choice([1, 2, 3, 4, 5])}}

    nb_filters.append({{choice([16, 32, 64])}})
    if conditional(n_layers) == 2:
        nb_filters.append({{choice([16, 32, 64])}})
    if conditional(n_layers) == 3:
        nb_filters.append({{choice([16, 32, 64])}})
        nb_filters.append({{choice([16, 32, 64])}})
    if conditional(n_layers) == 4:
        nb_filters.append({{choice([16, 32, 64])}})
        nb_filters.append({{choice([16, 32, 64])}})
        nb_filters.append({{choice([16, 32, 64])}})
    if conditional(n_layers) == 5:
        nb_filters.append({{choice([16, 32, 64])}})
        nb_filters.append({{choice([16, 32, 64])}})
        nb_filters.append({{choice([16, 32, 64])}})
        nb_filters.append({{choice([16, 32, 64])}})
        nb_filters.append({{choice([16, 32, 64])}})

    model = tcn.create_tcn(list_n_filters=nb_filters,
                           kernel_size=kernel_size,
                           dilations=dilations,
                           nb_stacks=nb_stacks,
                           n_layers=n_layers,
                           use_skip_connections=use_skip_connections,
                           dropout_rate={{uniform(0.05, 0.5)}})

    n_params = model.count_params()
    print("n_params: " + str(n_params))
    print(nb_filters)
    print(kernel_size)
    print(dilations)
    print(nb_stacks)
    if n_params > cfg["max_params"]:
        print("Too much parameters")
        return {'loss': np.inf, 'status': STATUS_OK, 'model': model}

    optimizer = optimizers.SGD(
        lr=cfg["optimizer"]["lr"], momentum=cfg["optimizer"]["momentum"], decay=cfg["optimizer"]["decay"])

    model.compile(loss=config.LOSS, metrics=config.METRICS,
                  optimizer=optimizer)

    result = model.fit_generator(train_set,
                                 epochs=cfg["n_epochs"],
                                 validation_data=val_set,
                                 workers=cfg["workers"],
                                 use_multiprocessing=cfg["use_multiprocessing"],
                                 shuffle=True
                                 )

    validation_loss = np.amin(result.history['val_loss'])
    print('Best validation acc of epoch:', validation_loss)
    return {'loss': validation_loss, 'status': STATUS_OK, 'model': model}


if __name__ == '__main__':
    best_run, best_model = optim.minimize(model=fit_tcn,
                                          data=data,
                                          algo=tpe.suggest,
                                          max_evals=100,
                                          trials=Trials())
    print("Best found values:")
    print(best_run)
