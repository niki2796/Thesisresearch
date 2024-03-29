import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.metrics import confusion_matrix, recall_score, accuracy_score, precision_score
from sklearn.metrics import roc_auc_score
from sklearn.metrics import roc_curve, auc
from tensorflow.keras import backend as K

LABELS = ["Normal","Anomaly"]

tf.random.set_seed(1121)
np.random.seed(1121)

def autoencoder_model(num_parallel, input_dim, encoding_dim, hidden_dim_1, hidden_dim_2):
    input_layer = tf.keras.layers.Input(shape=(input_dim, ))
    encoder = [None]*num_parallel
    decoder = [None]*num_parallel

    for i in range(num_parallel):

        encoder[i] = tf.keras.layers.Dense(encoding_dim, activation="elu",
                                        activity_regularizer=tf.keras.regularizers.l2(learning_rate))(input_layer)
        encoder[i]=tf.keras.layers.Dropout(0.2)(encoder[i])
        encoder[i] = tf.keras.layers.Dense(hidden_dim_1, activation='relu')(encoder[i])
        encoder[i] = tf.keras.layers.Dense(hidden_dim_2, activation=tf.nn.leaky_relu)(encoder[i])

        # Decoder
        decoder[i] = tf.keras.layers.Dense(hidden_dim_1, activation='relu')(encoder[i])
        decoder[i]=tf.keras.layers.Dropout(0.2)(decoder[i])
        decoder[i] = tf.keras.layers.Dense(encoding_dim, activation='relu')(decoder[i])
        decoder[i] = tf.keras.layers.Dense(input_dim, activation='elu')(decoder[i])

    #Autoencoder
    decoder = [K.expand_dims(a,axis=2) for a in decoder]
    decoder = tf.keras.layers.concatenate(decoder,axis=2)
    autoencoder = tf.keras.Model(inputs=input_layer, outputs=decoder)
    autoencoder.summary()
    return autoencoder

def autoenc_train(training_loss, x, nb_epoch, batch_size,num_parallel, input_dim, encoding_dim, hidden_dim_1, hidden_dim_2):

    autoencoder = autoencoder_model(num_parallel, input_dim, encoding_dim, hidden_dim_1, hidden_dim_2)

    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor='val_loss',
        min_delta=0.0001,
        patience=10,
        verbose=1,
        mode='min',
        restore_best_weights=True)

    autoencoder.compile(loss=training_loss,
                        optimizer='adam')

    history = autoencoder.fit(x, x,
                        epochs=nb_epoch,
                        batch_size=batch_size,
                        shuffle=True,
                        validation_split=0.2,
                        verbose=1,
                        callbacks=[early_stop]
                        ).history
    return autoencoder

def autoenc_predict(autoencoder,tx, ty, predict_loss, threshold_fixed= 0.65):
    test_x_predictions = autoencoder.predict(tx)
    score = predict_loss(tx, test_x_predictions, return_mean=False)
    error_df = pd.DataFrame({'Reconstruction_error': score, 'True_class': ty})
    #evaluation
    pred_y = [1 if e > threshold_fixed else 0 for e in error_df.Reconstruction_error.values]
    error_df['pred'] =pred_y
    conf_matrix = confusion_matrix(error_df.True_class, pred_y)
    roc = roc_auc_score(ty, score, average=None)
    return roc, score, error_df

def my_mse(tx, test_x_predictions, return_mean = False):
    return np.mean((np.mean(test_x_predictions, axis=-1) - tx) ** 2, axis=-1)

def loss_1(a,b, return_mean=True):
    q=b
    pd=[i for i in range(len(q.shape))]
    pd.remove(pd[-1])
    pd.insert(0,len(pd))
    q=K.permute_dimensions(q,tuple(pd))
    q=(q-a)**2
    if return_mean == False:
        return K.mean(q, axis=(0, -1))
    return K.mean(q)

def max_loss_1(a,b, return_mean=True):
    q=b
    pd=[i for i in range(len(q.shape))]
    pd.remove(pd[-1])
    pd.insert(0,len(pd))
    q=K.permute_dimensions(q,tuple(pd))
    q=(q-a)**2
    if return_mean == False:
        return K.max(K.mean(q, axis = -1), axis = 0)
    return K.mean(K.max(K.mean(q, axis = -1), axis = 0))

def s_loss_1(a, b):
    q = b
    pd = [i for i in range(len(q.shape))]
    pd.remove(pd[-1])
    pd.insert(0, len(pd))
    q = K.permute_dimensions(q, tuple(pd))
    q = (q - a) ** 2
    return K.mean(q)

def loss_2(a,b, return_mean=True):
    q=b
    pd=[i for i in range(len(q.shape))]
    pd.remove(pd[-1])
    pd.insert(0,len(pd))
    q=K.permute_dimensions(q,tuple(pd))
    q=K.square(a -  K.mean(q, axis=0))
    if return_mean == False:
        return K.mean(q, axis=-1)
    return K.mean(q)

def s_loss_2(a, b):
    return K.mean(K.square(K.mean(b, axis=2) - a))


def loss_3(a,b):
    q=b
    pd=[i for i in range(len(q.shape))]
    pd.remove(pd[-1])
    pd.insert(0, len(pd))
    q=K.permute_dimensions(q,tuple(pd))

    outdim = q.shape[0]

    q = (q - a)

    adl = None

    for i in range(outdim):
        for j in range(i + 1, outdim):
            ac = K.abs(K.mean(q[i] * q[j]))
            if adl is None:
                adl = ac
            else:
                adl += ac

    div = outdim * (outdim - 1) / 2
    return K.mean(adl) / div

def loss_4(a,b, return_mean=True):
    q=b
    pd=[i for i in range(len(q.shape))]
    pd.remove(pd[-1])
    pd.insert(0, len(pd))
    q=K.permute_dimensions(q,tuple(pd))
    outdim = q.shape[0]
    q = (q - a) ** 2  # rms
    q = K.mean(q, axis=-1)  # mean
    adl = None
    for i in range(outdim):
        for j in range(i + 1, outdim):
            ac = K.abs(K.mean(q[i] * q[j]))
            if adl is None:
                adl = ac
            else:
                adl += ac
    return adl


if __name__ == '__main__':
    bag = 1000 #Remove bagging as data set is small
    num_runs = 10 # no. of roc runs
    start = 3
    end = 60
    skip = 3
    a = np.load('cardio.npz')
    x = a['x']
    np.random.shuffle(x)
    x = x[:bag]
    y = np.zeros(len(x))
    tx = a['tx']
    ty = a['ty']
    nb_epoch = 100
    batch_size = 64
    input_dim = x.shape[1]
    encoding_dim = 14
    hidden_dim_1 = int(encoding_dim / 2) #
    hidden_dim_2 = 4
    learning_rate = 1e-7

    tr_loss = [loss_1, loss_1,  max_loss_1,  max_loss_1, loss_2, loss_3, loss_4]
    pr_loss = [my_mse, loss_1,  max_loss_1, my_mse, my_mse, my_mse, my_mse]
    store_values = np.zeros([int((end-start)/skip),len(tr_loss)])

    count = 0
    for itr in range(start, end, skip):
        num_parallel = itr
        print("No. of parallel auto encoders =", itr)

        for itr_loss in range(0, len(tr_loss)):
            training_loss = tr_loss[itr_loss]
            predict_loss = pr_loss[itr_loss]

            scores = []
            rocs = []
            for i in range(num_runs):
                print('Run: ',i)
                autoencoder = autoenc_train(training_loss, x, nb_epoch, batch_size,num_parallel, input_dim, encoding_dim, hidden_dim_1, hidden_dim_2)
                #reconstruct
                roc, score, error_df = autoenc_predict(autoencoder,tx, ty, predict_loss, threshold_fixed= 0.65)
                scores.append(score)
                rocs.append(roc)
            scores = np.array(scores)
            score = np.mean(scores, axis = 0)
            threshold_fixed = 0.65
            #pred_y = [1 if e > threshold_fixed else 0 for e in error_df.Reconstruction_error.values]
            #error_df['pred'] =pred_y
            #conf_matrix = confusion_matrix(error_df.True_class, pred_y)
            #roc = roc_auc_score(ty, score, average=None)
            roc = np.mean(np.array(rocs))
            print(roc)
            store_values[count][itr_loss] = roc
        count += 1
    np.save('stored_val.npy', store_values)
    x_ax = np.array([i for i in range(start, end, skip)])
    fig = plt.figure()
    for i in range(0, store_values.shape[1]):
        plt.plot(x_ax, store_values[:, i], label=str(tr_loss[i].__name__) + '-' + str(pr_loss[i].__name__))
    plt.title('ROCs of different losses vs number of ensembles')
    plt.xlabel('Number of Ensembles')
    plt.ylabel('ROC')
    plt.legend()
    plt.show()
    plt.savefig('loss_ens.png')

    fig2 = plt.figure()
    for i in range(0, 4):
        plt.plot(x_ax, store_values[:, i], label=str(tr_loss[i].__name__) + '-' + str(pr_loss[i].__name__))
    plt.title('ROC comparison of Multi dimensional MSE loss AGAINST Max MSE loss')
    plt.xlabel('Number of Ensembles')
    plt.ylabel('ROC')
    plt.legend()
    plt.show()
    plt.savefig('loss_ens_2.png')
