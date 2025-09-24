import nltk
from nltk.tokenize import word_tokenize
import pandas as pd
import matplotlib.pyplot as plt

sentence="Artificial intelligence (AI) has many different definitions; some see it as the created technology that allows computers and machines to function intelligently. Some see it as the machine that replaces human labor to work for men a more effective and speedier result. Others see it as “a system” with the ability to correctly interpret external data, to learn from such data, and to use those learnings to achieve specific goals and tasks through flexible adaptation"
tokens = word_tokenize(sentence)
print(tokens)
unigrams = (pd.Series(nltk.ngrams(tokens, 1)).value_counts())
print(unigrams)
unigrams[:10].sort_values().plot.barh(color='green', width=9, figsize=(12,8))
plt.title("10 most commonly used words")

