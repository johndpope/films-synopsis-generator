"""
Data loading, preprocessing and generation
"""

import settings

import os
import numpy as np
import pandas as pd
import re

from sklearn.preprocessing import MultiLabelBinarizer
from collections import defaultdict
from sklearn.externals import joblib
from nltk.tag import pos_tag

class Preprocessor():

    def __init__(self):
        """
        Loads the films csv (genres and synopsis)
        Preprocesses both of them and keeps them in memory
        Initialises
        """
        #Attributes list (initialised afterwards in this method)
        self.index_to_word = None #{ 3:'hola', 3002: 'cielo' ...
        self.word_to_index = None #{'hola': 3, 'cielo': 3002, ...
        self.mlb = None
        self.encoded_genres = None
        self.synopses = None
        self.count = 0

    
    def build_indexes(self):
        settings.logger.info("Building word indexes")
        #print(str(unique).encode('latin1'))
        self.word_to_index = {}
        self.index_to_word = {}

        for i, word in enumerate(self.vocabulary):
            self.word_to_index[word]=i
            self.index_to_word[i]=word
        assert len(self.word_to_index) == len(self.index_to_word)
        joblib.dump(self.word_to_index, os.path.join(settings.OTHERS_DIR, 'word_to_index.pkl'))
        joblib.dump(self.index_to_word, os.path.join(settings.OTHERS_DIR, 'index_to_word.pkl'))
        settings.logger.info("Saved index dictionaries for "+str(len(self.word_to_index))+" words in "+settings.OTHERS_DIR)
        
    def preprocess_synopses(self, df):
        settings.logger.info("Preprocessing synopses...")

        #Keep the synopsis as a list
        self.synopses = df['Synopsis'].map(self.clean_text)

        settings.logger.info("Tokenizing synopses...")
        self.synopses = self.synopses.map(self.tokenize)

        self.synopses = list(self.synopses.values)
         
        from collections import defaultdict

        settings.logger.info("Counting word frequency...")
        word_freqs = defaultdict(int)
        for synopsis in self.synopses:
            for word in synopsis:
                word_freqs[word] += 1
                
        word_freqs = list(word_freqs.items())
        most_frequent = sorted(word_freqs, key = lambda x: x[1], reverse = True)
        settings.logger.info("Most frequent words: " + str(most_frequent[:10]))
        
        self.vocabulary = [w[0] for w in most_frequent][:settings.VOCABULARY_SIZE]
        self.vocabulary[-1] = settings.UNKNOWN_TOKEN
        if settings.EOS_TOKEN not in self.vocabulary:
            self.vocabulary[-2] = settings.EOS_TOKEN
        settings.logger.info("Only "+str(len(self.vocabulary))+" words will be considered (VOCABULARY_SIZE)")

        #Substitute any unkown word with <unk> token inside the function.
        self.count = 0
        self.total = len(self.synopses)
        def map_unkown_tokens(obj, synopsis):
            new_synopsis = []
            for word in synopsis:
                if word in self.vocabulary:
                    new_synopsis.append(word)
                else:
                    new_synopsis.append(settings.UNKNOWN_TOKEN)
            obj.count += 1
            if obj.count % 100 == 0:
                settings.logger.info(str(100*obj.count/obj.total)[:4]+'% completed...')
            return new_synopsis
        settings.logger.info("Mapping unkown tokens...")
        #self.synopses = [map_unkown_tokens(synopsis) for synopsis in self.synopses]
        self.synopses = list(pd.Series(self.synopses).map(lambda x: map_unkown_tokens(self,x)))

    ''' Receives a string.
       Returns that same string after being preprocessed.'''

    def clean_text(self, text):
        # Handle (...)
        #text = 'asdas 9999 asdasdsd , hola... ! 787 8 '
        text_in_paren = re.findall("\([^\)]*\)", text)
        if text_in_paren:
            for del_text in text_in_paren:
                text = text.replace(del_text, '')
        # Handle digits
        digits = re.findall(r'\d+', text)
        if digits:
            for digit in digits:
                text = text.replace(digit, settings.DIGIT_TOKEN)
        # Remove puntuaction
        # text = "".join(c for c in text if c not in ('¡','!','¿','?', ':', ';'))
        text = re.sub(r'[^a-zA-Z\.áéíóúÁÉÍÓÚüÜñÑ]', ' ', text)
        # Remove extra spaces that were left when cleaning
        text = re.sub(r'\s+', ' ', text)
        
        #text = text.lower()
        text_tags = pos_tag(text.split())
        final = ""
        for word, pos in text_tags:
            if pos == "NPP" or word == settings.DIGIT_TOKEN:
                final += " " + word
            else:
                final += " " + word.lower()
        self.count +=1
        if self.count % 1000 == 0:
            settings.logger.info(self.count)
        return final
        
    def filter_dataset(self):
        """
        This is meant to be the last preprocessing step. It reduces the
        dataset and should be called after preprocess_synopsis and
        preprocess_genres
        """
        filtered_genres, filtered_synopses = [], []
        for genres, synopsis in zip(self.genres, self.synopses):
            known_words = len(synopsis) - synopsis.count(settings.UNKNOWN_TOKEN)
            if known_words / len(synopsis) < settings.MINIMUM_KNOWN_PERC_TOKENS_PER_SYNOPSIS:
                continue
            if len(genres) == 0:
                continue
            filtered_genres.append(genres)
            filtered_synopses.append(synopsis)
        self.genres = filtered_genres
        self.synopses = filtered_synopses    
     
        #settings.logger.info("Total tokens in corpus after preprocessing : "+str(corpus_tokens_count))
        
    def save_data(self):
        assert len(self.genres) == len(self.synopses)
        films_preprocessed = [self.encoded_genres, self.encoded_synopses]
        filepath = os.path.join(settings.DATA_DIR,str("preprocessed_films.pkl"))
        #print(films_preprocessed)
        joblib.dump(films_preprocessed, filepath)
        settings.logger.info(str(len(self.encoded_genres))+" preprocessed films data saved to "+filepath) 
        
    
    def encode_genres(self):   
        #Preprocess genres (multilabel)
        self.encoded_genres = self.mlb.transform(self.genres)
        settings.logger.info(str(len(self.mlb.classes_))+" different genres found:"+str(self.mlb.classes_)[:100]+"...")
        #I am not sure when to use .encode('latin1')
        settings.logger.debug('Genres vector shape: '+str(self.encoded_genres.shape)) 
        settings.logger.info('Genres encoded')
    
    def encode_synopses(self):
        self.encoded_synopses = []
        for synopsis in self.synopses:
            encoded_synopsis = []
            for word in synopsis:
                encoded_synopsis.append(self.word_to_index[word])
            self.encoded_synopses.append(encoded_synopsis)

        settings.logger.info('Synopses encoded')
    
    def load_dataset(self):
        import pandas as pd
        if settings.USE_SMALL_DATASET:
            nrows = 5000
        else:
            nrows = None
        df = pd.read_csv(filepath_or_buffer  = os.path.join(settings.DATA_DIR,'synopsis_genres.csv'),sep = '#',encoding = 'latin_1',index_col = 'ID', nrows = nrows)
        df = df[df['Synopsis'].notnull() & df['Genre'].notnull()]
        settings.logger.info(str(df.info()))
        #settings.logger.info(str(df[['Genre','Synopsis']][:5]).encode('latin1'))
        return df
        
    def generate_embedding_weights(self):        
        settings.logger.info('Loading Word2Vec model from '+settings.WORD2VEC_MODEL_PATH)
        if settings.USE_SMALL_WORD2VEC:
            nrows = 100000
        else:
            nrows = None
        model = pd.read_csv(settings.WORD2VEC_MODEL_PATH, sep = ' ', header = None, \
                            index_col = 0, skiprows = 1, nrows = nrows)
        settings.logger.info('Generating embedding weights matrix...')
        embedding_rows = len(self.vocabulary) + 1 # adding 1 to account for 0th index (for masking)
        embedding_weights = np.zeros((embedding_rows,settings.EMBEDDING_DIM))
        count = 0
        for index, word in enumerate(self.vocabulary):
            #print(self.index_to_word[index],word)
            try:
                embedding_weights[index,:] = model.loc[word].values
            except KeyError:
                settings.logger.warning(self.index_to_word[index]+' ('+word+') not found in word2vec')
                count += 1

        #embedding_weights[embedding_rows-1, :] = settings.EOS_TOKEN
        settings.logger.info(str(count)+" tokens represented with zeros in the weight matrix "+str(embedding_weights.shape))

        joblib.dump(embedding_weights, settings.EMBEDDING_WEIGHTS_PATH)
        settings.logger.info("Saved weights matrix in "+settings.EMBEDDING_WEIGHTS_PATH)
        
    def preprocess_genres(self, df):
        
        self.genres = list(df['Genre'].map(lambda x: x.split('|')))

            
        genre_freqs = defaultdict(int)
        for genres_ in self.genres:
            for genre in genres_:
                genre_freqs[genre] += 1
        
        genre_freqs = list(genre_freqs.items())        
        most_frequent = sorted(genre_freqs, key = lambda x: x[1], reverse = True)
        settings.logger.info("Most frequent genres: " + str(most_frequent[:10]))
        
        knwown_genres = [g[0] for g in most_frequent][:settings.MAX_GENERES]
        
        settings.logger.info("Only "+str(len(knwown_genres))+" genres will be considered (MAX_GENERES)")
        
        def delete_unkown_genres(fgenres):
            return [genre for genre in fgenres if genre in knwown_genres]
            
        self.genres = [delete_unkown_genres(fgenres) for fgenres in self.genres]      
        
        self.mlb = MultiLabelBinarizer()
        self.mlb.fit(self.genres)
        #settings.logger.info(str(len(self.mlb.classes_))+" different genres found:"+str(self.mlb.classes_)[:100]+"...")
        #I am not sure when to use .encode('latin1')        
        filepath = os.path.join(settings.OTHERS_DIR, 'genre_binarizer_'+str(len(self.mlb.classes_))+'_classes.pkl')
        joblib.dump(self.mlb, filepath)
        settings.logger.info(filepath+' saved')

        
    def tokenize(self,s):
        """
        Tokenize the synopsis, example:
        'HOLAA!! ¿Qué tal estaás?'  -> 'holaa ! ! ¿ qué tal estás ?<eos>'
        """
        return re.findall(r"[\w]+|[^\s\w]", s) + [settings.EOS_TOKEN]


class Generator():
    def __init__(self, synopses, genres):
        self.synopses = synopses
        self.genres = genres

    # def get_train_val_generators(self, ):
    #
    #     X_train, X_test, y_train, y_test = train_test_split(
    #         self.synopses, self.genres, test_size = settings.VALIDATION_SPLIT, random_seed = 42)
    #     generator_train = self.generate(X_train, y_train)
    #     #self.generator_train.initialize()
    #     generator_val = self.generate(X_test, y_test)
    #     return generator_train, generator_val

    def load_indexes(self):
        self.word_to_index = joblib.load(os.path.join(settings.WORD_TO_INDEX_PATH))
        self.index_to_word = joblib.load(os.path.join(settings.INDEX_TO_WORD_PATH))
        settings.logger.info("Loaded index dictionaries")

    def load_genre_binarizer(self):
        filepath = settings.GENRE_BINARIZER_PATH
        self.mlb = joblib.load(filepath)
        settings.logger.info(filepath+' loaded')

    # def load_preprocessed_data(self):
    #     """
    #     Loads preprocessed lists of synopses and genres
    #     """
    #     films_preprocessed = joblib.load(settings.INPUT_PREPROCESSED_FILMS)
    #
    #     self.synopses = films_preprocessed[1]
    #     self.genres = films_preprocessed[0]
    #     settings.logger.info("Loaded preprocessed films from "+str(settings.INPUT_PREPROCESSED_FILMS))
    #     settings.logger.info(self.synopses[0][:10])
    #     settings.logger.info(self.genres[0])

    def to_genre(self, vector):
        """
        [0,0,1,0,1...] -> 'drama|comedia'
        """
        
        return '|'.join(self.mlb.inverse_transform(vector[None, :])[0])


    def to_synopsis(self, vector):
        """
        Converts a vector of words (i.e. a vector of vectors) into its
        text representation
        """
        return ' '.join([self.index_to_word[i] for i in vector])

    def generate(self):
        """
        Generate batches to feed the network.
        Batches are comprised of ((genre, previous_words), next_words))
        """
        #from keras.preprocessing import sequence
        # Initialize batch variables
        previous_words_batch = []
        next_word_batch = []
        genres_batch = []

        settings.logger.info("Generating data...  ")

        # Keep track of how many batches have been fed
        batches_fed_count = 0
        while 1:
            # Keep track of the current batch that is being built
            current_batch_size = 0

            synopsis_counter = -1
            # Iterate over all the synopsis

            for synopsis in self.synopses:
                synopsis_counter += 1
                genre = self.genres[synopsis_counter]
                # Itearte over synopsis' words
                

                for i in range(len(synopsis) - 1):
                    # Grab next word and add it to the current batch
                    next_word = synopsis[i + 1]
                    next_word_batch.append(next_word)

                    # Grab previous words and add them to the current batch
                    previous_words = [word for word in synopsis[:i + 1]]
                    previous_words_batch.append(previous_words)

                    # Add the genre to the batch
                    genres_batch.append(genre)

                    # Increment batch size
                    current_batch_size += 1

                    if current_batch_size < settings.BATCH_SIZE:
                        # Keep building the batch
                        continue
                    # Batch is ready
                    next_word_batch = np.asarray(next_word_batch)
                    genres_batch = np.asarray(genres_batch)

                    # Padd previous words of synopses
                    '''
                    #previous_words_batch = sequence.pad_sequences(previous_words_batch,
                                                                  maxlen=settings.MAX_SYNOPSIS_LEN, padding='post')
                    '''
                    # print(len(genres_batch),genres_batch[0].shape,previous_words_batch.shape,next_word_batch.shape)
                    # print(next_word_batch.mean())
                    '''
                    if 0:
                        for j in range(settings.batch_size):
                            print(str(self.to_genre(genres_batch[j])).encode('latin1'))
                            print(str(self.to_synopsis(previous_words_batch[j])).encode('latin1'))
                            print(str(self.to_synopsis(np.nonzero(next_word_batch[j])[0])).encode('latin1'))
                            print("************")
                        print("____________________________________________")
                    '''
                    # Yield batch
                    yield [[genres_batch, previous_words_batch], next_word_batch]
                    batches_fed_count += 1
                    # settings.logger.info("Batches yielded: "+str(batches_fed_count))

                    # Reset variables
                    previous_words_batch = []
                    next_word_batch = []
                    genres_batch = []
                    current_batch_size = 0

