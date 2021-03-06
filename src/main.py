import os
import data
import settings
import model
from sklearn.externals import joblib
import pickle as pk
import numpy as np
from sklearn.model_selection import train_test_split
import nltk

def test_generator():

    synopses, genres = load_preprocessed_data(settings.INPUT_PREPROCESSED_FILMS)
    X_train, X_val, y_train, y_val = train_test_split(
        synopses, genres, test_size=settings.VALIDATION_SPLIT)
    c= data.Generator(X_train, y_train)
    c.load_genre_binarizer()
    c.load_indexes()
    #a = g.generate().__next__()
    #g.get_train_val_generators()
    from time import sleep


    while 1:
        for a,b in c.generate():
            for i in range(a[0].shape[0]):
                print(c.to_genre(a[0][i]),a[0][i].shape)
                print(c.to_synopsis(a[1][i]),len(a[1][i]),type(a[1][i][0]))
                print(c.index_to_word[b[i]],type(b[i]))
                print('_______________________________________')

            
def generate_files():

    preprocessor = data.Preprocessor()
    df = preprocessor.load_dataset()
    
    preprocessor.preprocess_synopses(df)
    preprocessor.preprocess_genres(df)
    preprocessor.build_indexes()
    preprocessor.generate_embedding_weights()
    preprocessor.filter_dataset()
    preprocessor.encode_genres()
    preprocessor.encode_synopses()
    preprocessor.save_data()

def check_paths():
    if not os.path.exists(settings.DATA_DIR):
        os.makedirs(settings.DATA_DIR)

    if not os.path.exists(settings.OTHERS_DIR):
        os.makedirs(settings.OTHERS_DIR)

    if not os.path.exists(settings.WEIGHTS_DIR):
        os.makedirs(settings.WEIGTHS_DIR)

    if not os.path.exists(settings.TENSORBOARD_LOGS_DIR):
        os.makedirs(settings.TENSORBOARD_LOGS_DIR)

def check_nltk_resources():
    nltk.download('averaged_perceptron_tagger')


def train_network():

    synopses, genres = load_preprocessed_data(settings.INPUT_PREPROCESSED_FILMS)
    X_train, X_val, y_train, y_val = train_test_split(
        synopses, genres, test_size=settings.VALIDATION_SPLIT)

    network = model.Network()
    network.load_generators(X_train, X_val, y_train, y_val)       # Synopses and genres as parameter
    network.load_embeddings()
    network.build()
    #network.load_weights()
    network.compile()
    network.train()


def load_preprocessed_data(path):
    """
    Loads preprocessed lists of synopses and genres
    """
    films_preprocessed = joblib.load(path)
#    films_preprocessed = pk.load(path)
    genres = films_preprocessed[0]
    synopses = films_preprocessed[1]
    settings.logger.info("Loaded preprocessed films from " + str(path))
    return synopses, genres


if __name__ == '__main__':
    check_nltk_resources()
    check_paths()
    #generate_files()
    #test_generator()
    train_network()
