import re
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# text_preprocesing

def text_preprocess(text):
    # lowercase
    text = text.lower()
    # remove special characters and numbers
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    # remove extra spaces
    text = re.sub(r'[\s+]', ' ', text)
    # tokenize
    tokens = text.split()
    # remove stopwords
    tokens = [word for word in tokens if word not in ENGLISH_STOP_WORDS]
    
    return ' '.join(tokens)


        