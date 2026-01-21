import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load data
diamonds = pd.read_csv("diamonds.csv")

# Basic info
print(diamonds.info())
print(diamonds.describe())

# Univariate: Price distribution
sns.histplot(diamonds['price'], bins=50, kde=True)
plt.title('Price Distribution')
plt.show()

# Bar plot: Count of diamonds by cut
sns.countplot(x='cut', data=diamonds)
plt.title('Diamonds by Cut')
plt.show()

# Bivariate: Price vs. Carat
sns.scatterplot(x='carat', y='price', data=diamonds, hue='cut')
plt.title('Price vs. Carat by Cut')
plt.show()

# Boxplot: Price by Clarity
sns.boxplot(x='clarity', y='price', data=diamonds)
plt.title('Price by Clarity')
plt.show()

# Heatmap: Correlation matrix
corr = diamonds.corr(numeric_only=True)
sns.heatmap(corr, annot=True, fmt=".2f")
plt.title('Correlation Matrix')
plt.show()