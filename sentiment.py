import argparse
import openai
from sklearn.manifold import TSNE
import plotly.graph_objs as go
from utils import load_articles
from tqdm import tqdm
from config import OPENAI_KEY
import os
import pickle
import numpy as np

openai.api_key = OPENAI_KEY


def generate_embeddings(articles, force=False):
  if os.path.exists('embeddings.pkl') and not force:
    print("Loading embeddings from file...")
    with open('embeddings.pkl', 'rb') as f:
      embeddings = pickle.load(f)
  else:
    print("Generating embeddings...")
    model_id = "text-embedding-ada-002"
    embeddings = {}
    for i, (title, text) in enumerate(
        tqdm(articles.items(), desc="Embedding articles")):
      text_string = '\n'.join([title, text])
      response = openai.Embedding.create(input=text_string, model=model_id)
      embeddings[title] = response['data'][0]['embedding']

    print("Saving embeddings to file...")
    with open('embeddings.pkl', 'wb') as f:
      pickle.dump(embeddings, f)

  return embeddings


def generate_tsne(embeddings, force=False):
  if os.path.exists('tsne.pkl') and not force:
    print("Loading TSNE values from file...")
    with open('tsne.pkl', 'rb') as f:
      tsne_dict = pickle.load(f)
    print("TSNE values loaded.")
  else:
    print("Generating TSNE values...")
    tsne_model = TSNE(n_components=2,
                      perplexity=5,
                      init='pca',
                      n_iter=2500,
                      random_state=23)
    new_values = tsne_model.fit_transform(np.array(list(embeddings.values())))
    tsne_dict = {}
    for k, n_v in zip(embeddings.keys(), new_values):
      tsne_dict[k] = n_v

    print("Saving TSNE values to file...")
    with open('tsne.pkl', 'wb') as f:
      pickle.dump(tsne_dict, f)

  return tsne_dict


def plot_tsne(tsne_dict):
  x_vals = [value[0] for value in tsne_dict.values()]
  y_vals = [value[1] for value in tsne_dict.values()]
  titles = [title[:20] for title in tsne_dict.keys()]

  trace = go.Scatter(x=x_vals,
                     y=y_vals,
                     mode='markers',
                     text=titles,
                     hoverinfo='text',
                     marker=dict(
                       sizemode='diameter',
                       sizeref=0.85,
                       size=25,
                       opacity=0.5,
                     ))

  data = [trace]

  layout = go.Layout(title='TSNE Values',
                     width=800,
                     height=600,
                     autosize=False,
                     showlegend=False,
                     hovermode='closest')

  fig = go.Figure(data=data, layout=layout)
  fig.show()


if __name__ == "__main__":
  parser = argparse.ArgumentParser(
    description="Force recalculation of embeddings and t-SNE values.")
  parser.add_argument('-f',
                      '--force',
                      action='store_true',
                      help="Force recalculation even if files exist.")

  args = parser.parse_args()

  articles = load_articles()
  embeddings = generate_embeddings(articles, force=args.force)
  tsne_values = generate_tsne(embeddings, force=args.force)
  plot_tsne(tsne_values)
