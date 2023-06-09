import os
import streamlit as st
from webscraper import scrape_be
from config import BE_JSY_URL, HEADERS
from script import gpt_generate, gpt_translate
from utils import save_articles, load_articles


def main():
  # Add the app functionality here
  st.title('AI News Summary Demo')

  if st.button("Start Demo"):
    with st.spinner("Scraping Bailiwick Express..."):
      articles, current_date = scrape_be(BE_JSY_URL, headers=HEADERS)
      articles_save_path = os.path.join(os.getcwd(), 'data', current_date,
                                        'raw_articles.json')
      save_articles(articles, articles_save_path)
    #st.markdown("**Articles found:**")
    #st.markdown("\n".join([f"- **{title}**" for title, _ in articles.items()]))

    with st.spinner("Generating AI Summary..."):
      english_script = gpt_generate(
        articles)  # Generate the English podcast script
    st.markdown(english_script)

    with st.spinner("Generating AI Translations..."):
      pt_script = gpt_translate(
        english_script, 'portuguese')  # Generate the Portuguese podcast script
      pl_script = gpt_translate(english_script,
                                'polish')  # Generate the Polish podcast script

    col1, col2 = st.columns(2)
    with col1:
      st.subheader('Portuguese Translation')
      st.markdown(pt_script)
    with col2:
      st.subheader('Polish Translation')
      st.markdown(pl_script)

    with st.button('Generating advanced AI audio...'):
      


if __name__ == '__main__':
  main()
