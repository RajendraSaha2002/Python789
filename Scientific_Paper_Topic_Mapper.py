import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt

# Load abstracts CSV: columns: id, title, abstract
df = pd.read_csv("abstracts.csv").dropna(subset=["abstract"])
tfidf = TfidfVectorizer(max_df=0.8, min_df=10, stop_words='english')
X = tfidf.fit_transform(df.abstract)

n_topics = 10
nmf = NMF(n_components=n_topics, random_state=42)
W = nmf.fit_transform(X)
H = nmf.components_

def top_terms(topic_idx, n=8):
    finds = H[topic_idx].argsort()[::-1][:n]
    return [tfidf.get_feature_names_out()[i] for i in finds]

for t in range(n_topics):
    print(f"Topic {t}: {', '.join(top_terms(t))}")

tsne = TSNE(perplexity=30, random_state=42).fit_transform(W)
plt.scatter(tsne[:,0], tsne[:,1], c=W.argmax(axis=1), cmap='tab10', s=10)
plt.title("Abstract Topic Map")
plt.show()