# src/sentiment_analyzer.py
import requests
import tweepy
import re
from datetime import datetime, timedelta
import time
from typing import Dict, List
import logging
from config.settings import Config

class SentimentAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Twitter API credentials (jeśli masz)
        self.twitter_bearer_token = Config.TWITTER_BEARER_TOKEN if hasattr(Config, 'TWITTER_BEARER_TOKEN') else None
        
        # CryptoPanic API
        self.cryptopanic_api_key = Config.CRYPTOPANIC_API_KEY if hasattr(Config, 'CRYPTOPANIC_API_KEY') else None
        
        # Initialize clients
        self.twitter_client = None
        if self.twitter_bearer_token:
            self.twitter_client = tweepy.Client(bearer_token=self.twitter_bearer_token)
    
    def get_twitter_sentiment(self, query: str = "bitcoin OR BTC", max_results: int = 100) -> Dict:
        """Analizuje sentyment z Twittera"""
        if not self.twitter_client:
            self.logger.warning("Twitter client not configured")
            return {'error': 'Twitter not configured'}
        
        try:
            # Szukaj tweetów z ostatniej godziny
            tweets = self.twitter_client.search_recent_tweets(
                query=query + " -is:retweet lang:en",
                max_results=max_results,
                tweet_fields=['created_at', 'author_id', 'public_metrics']
            )
            
            if not tweets.data:
                return {'sentiment_score': 0, 'tweet_count': 0}
            
            sentiment_scores = []
            for tweet in tweets.data:
                score = self._analyze_tweet_sentiment(tweet.text)
                sentiment_scores.append(score)
            
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            
            return {
                'sentiment_score': avg_sentiment,
                'tweet_count': len(tweets.data),
                'positive_ratio': len([s for s in sentiment_scores if s > 0]) / len(sentiment_scores) if sentiment_scores else 0,
                'negative_ratio': len([s for s in sentiment_scores if s < 0]) / len(sentiment_scores) if sentiment_scores else 0,
                'neutral_ratio': len([s for s in sentiment_scores if s == 0]) / len(sentiment_scores) if sentiment_scores else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching Twitter sentiment: {e}")
            return {'error': str(e)}
    
    def _analyze_tweet_sentiment(self, text: str) -> float:
        """Podstawowa analiza sentymentu tweeta"""
        # Słowa kluczowe
        positive_words = ['bullish', 'moon', 'pump', 'gain', 'up', 'high', 'buy', 'long', 'profit', 'green', 'breakout', 'rally']
        negative_words = ['bearish', 'dump', 'crash', 'down', 'low', 'sell', 'short', 'loss', 'red', 'breakdown', 'drop']
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        # Prosty scoring: +1 za pozytywne, -1 za negatywne
        sentiment_score = positive_count - negative_count
        
        # Normalizacja do zakresu [-1, 1]
        max_score = max(positive_count + negative_count, 1)
        return sentiment_score / max_score
    
    def get_cryptopanic_news(self, currencies: str = "BTC", filter: str = "rising") -> Dict:
        """Pobiera wiadomości z CryptoPanic"""
        if not self.cryptopanic_api_key:
            self.logger.warning("CryptoPanic API key not configured")
            return {'error': 'CryptoPanic not configured'}
        
        try:
            url = f"https://cryptopanic.com/api/v1/posts/"
            params = {
                'auth_token': self.cryptopanic_api_key,
                'currencies': currencies,
                'filter': filter,
                'public': 'true'
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'results' not in data:
                return {'error': 'No results found'}
            
            news_items = data['results']
            
            # Analiza sentymentu wiadomości
            sentiment_scores = []
            for item in news_items:
                title = item.get('title', '')
                score = self._analyze_news_sentiment(title)
                sentiment_scores.append(score)
            
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            
            # Votes analysis
            total_positive = sum(item.get('votes', {}).get('positive', 0) for item in news_items)
            total_negative = sum(item.get('votes', {}).get('negative', 0) for item in news_items)
            total_votes = total_positive + total_negative
            
            return {
                'news_count': len(news_items),
                'avg_sentiment': avg_sentiment,
                'positive_votes': total_positive,
                'negative_votes': total_negative,
                'vote_ratio': total_positive / total_votes if total_votes > 0 else 0.5,
                'latest_news': [{'title': item.get('title'), 'created_at': item.get('created_at')} 
                               for item in news_items[:5]]
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching CryptoPanic data: {e}")
            return {'error': str(e)}
    
    def _analyze_news_sentiment(self, text: str) -> float:
        """Analizuje sentyment nagłówka wiadomości"""
        # Słowa kluczowe dla wiadomości
        positive_words = ['surge', 'rally', 'gain', 'rise', 'bullish', 'adoption', 'upgrade', 'support', 'breakout', 'ath']
        negative_words = ['crash', 'plunge', 'drop', 'fall', 'bearish', 'ban', 'hack', 'scam', 'breakdown', 'lawsuit']
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        sentiment_score = positive_count - negative_count
        max_score = max(positive_count + negative_count, 1)
        
        return sentiment_score / max_score
    
    def get_reddit_sentiment(self, subreddit: str = "cryptocurrency", limit: int = 100) -> Dict:
        """Analizuje sentyment z Reddita"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
            
            response = requests.get(url, headers=headers)
            data = response.json()
            
            if 'data' not in data or 'children' not in data['data']:
                return {'error': 'No data found'}
            
            posts = data['data']['children']
            sentiment_scores = []
            
            for post in posts:
                title = post['data'].get('title', '')
                score = self._analyze_reddit_sentiment(title)
                sentiment_scores.append(score)
            
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            
            return {
                'post_count': len(posts),
                'avg_sentiment': avg_sentiment,
                'top_posts': [{'title': p['data'].get('title'), 'score': p['data'].get('score')} 
                             for p in posts[:5]]
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching Reddit sentiment: {e}")
            return {'error': str(e)}
    
    def _analyze_reddit_sentiment(self, text: str) -> float:
        """Analizuje sentyment posta z Reddita"""
        # Podobna logika jak dla Twittera
        return self._analyze_tweet_sentiment(text)
    
    def get_overall_sentiment(self) -> Dict:
        """Pobiera ogólny sentyment z wszystkich źródeł"""
        sentiment_data = {}
        
        # Twitter
        twitter_sentiment = self.get_twitter_sentiment()
        if 'error' not in twitter_sentiment:
            sentiment_data['twitter'] = twitter_sentiment
        
        # CryptoPanic
        news_sentiment = self.get_cryptopanic_news()
        if 'error' not in news_sentiment:
            sentiment_data['news'] = news_sentiment
        
        # Reddit
        reddit_sentiment = self.get_reddit_sentiment()
        if 'error' not in reddit_sentiment:
            sentiment_data['reddit'] = reddit_sentiment
        
        # Oblicz średni sentyment
        sentiment_scores = []
        weights = {'twitter': 0.4, 'news': 0.4, 'reddit': 0.2}
        
        for source, data in sentiment_data.items():
            if source in weights and 'sentiment_score' in data:
                score = data.get('sentiment_score', 0) * weights[source]
                sentiment_scores.append(score)
        
        overall_sentiment = sum(sentiment_scores) if sentiment_scores else 0
        
        # Decyzja na podstawie sentymentu
        sentiment_signal = 'neutral'
        if overall_sentiment > 0.2:
            sentiment_signal = 'bullish'
        elif overall_sentiment < -0.2:
            sentiment_signal = 'bearish'
        
        return {
            'overall_sentiment': overall_sentiment,
            'sentiment_signal': sentiment_signal,
            'sources': sentiment_data,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_fear_greed_index(self) -> Dict:
        """Pobiera Fear & Greed Index"""
        try:
            url = "https://api.alternative.me/fng/"
            response = requests.get(url)
            data = response.json()
            
            if 'data' in data and len(data['data']) > 0:
                current = data['data'][0]
                return {
                    'value': int(current['value']),
                    'classification': current['value_classification'],
                    'timestamp': current['timestamp']
                }
            
            return {'error': 'No data available'}
            
        except Exception as e:
            self.logger.error(f"Error fetching Fear & Greed Index: {e}")
            return {'error': str(e)}