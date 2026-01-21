from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer

text = """
Artificial intelligence (AI) is transforming industries and daily life. It enables computers to learn from data, 
identify patterns, and make decisions with minimal human intervention. With advances in deep learning and natural 
language processing, AI is now capable of performing complex tasks such as image recognition, language translation, 
and autonomous driving. As AI continues to evolve, it is expected to have a profound impact on society, 
raising both opportunities and challenges.
"""

parser = PlaintextParser.from_string(text, Tokenizer("english"))
summarizer = LexRankSummarizer()
summary = summarizer(parser.document, sentences_count=2)
print("Summary:")
for sentence in summary:
    print(sentence)