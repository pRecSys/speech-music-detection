from keras.models import Input, Model
from keras.layers import Dense, ConvLSTM2D, Bidirectional, TimeDistributed, Reshape
from smd import config


def create_b_conv_lstm(filters_list, kernel_size_list, stride_list, dilation_rate_list, dropout=0.05):
    input_layer = Input(shape=(None, config.N_MELS))
    x = Reshape((-1, 1, 1, config.N_MELS))(input_layer)

    for i in range(len(filters_list)):
        x = Bidirectional(ConvLSTM2D(filters_list[i],
                                     kernel_size_list[i],
                                     strides=stride_list[i],
                                     padding='same',
                                     data_format='channels_last',
                                     dilation_rate=dilation_rate_list[i],
                                     return_sequences=True,
                                     dropout=dropout))(x)
    print(x._keras_shape)
    x = Reshape((-1, x._keras_shape[4]))(x)
    output_layer = TimeDistributed(Dense(config.CLASSES, activation='sigmoid'))(x)
    model = Model(input_layer, output_layer)

    return model
