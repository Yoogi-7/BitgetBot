# src/sentiment_analyzer.py
import requests
import praw
import tweepy
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import logging
from config.settings import Config


class EnhancedSentimentAnalyzer:
    """Enhanced sentiment analysis from multiple sources."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sentiment_cache = {}
        self.last_update = {}
        
        # Initialize API clients
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize API clients for different platforms."""
        # Twitter/X client
        if Config.TWITTER_BEARER_TOKEN:
            try:
                self.twitter_client = tweepy.Client(bearer_token=Config.TWITTER_BEARER_TOKEN)
                self.logger.info("Twitter client initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Twitter client: {e}")
                self.twitter_client = None
        
        # Reddit client
        if Config.REDDIT_CLIENT_ID and Config.REDDIT_CLIENT_SECRET:
            try:
                self.reddit_client = praw.Reddit(
                    client_id=Config.REDDIT_CLIENT_ID,
                    client_secret=Config.REDDIT_CLIENT_SECRET,
                    user_agent='CryptoSentimentBot/1.0'
                )
                self.logger.info("Reddit client initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Reddit client: {e}")
                self.reddit_client = None
    
    def get_comprehensive_sentiment(self) -> Dict:
        """Get sentiment from all available sources."""
        sentiment_data = {
            'overall_sentiment': 'neutral',
            'overall_score': 0,
            'sources': {},
            'timestamp': datetime.now()
        }
        
        # Collect from each source
        if self._should_update('twitter'):
            twitter_sentiment = self._get_twitter_sentiment()
            if twitter_sentiment:
                sentiment_data['sources']['twitter'] = twitter_sentiment
        
        if self._should_update('reddit'):
            reddit_sentiment = self._get_reddit_sentiment()
            if reddit_sentiment:
                sentiment_data['sources']['reddit'] = reddit_sentiment
        
        if self._should_update('fear_greed'):
            fear_greed = self._get_fear_greed_index()
            if fear_greed:
                sentiment_data['sources']['fear_greed'] = fear_greed
        
        if self._should_update('news'):
            news_sentiment = self._get_news_sentiment()
            if news_sentiment:
                sentiment_data['sources']['news'] = news_sentiment
        
        # Calculate weighted overall sentiment
        weighted_scores = []
        for source, data in sentiment_data['sources'].items():
            if 'score' in data and source in Config.SENTIMENT_WEIGHT:
                weighted_scores.append(data['score'] * Config.SENTIMENT_WEIGHT[source])
        
        if weighted_scores:
            sentiment_data['overall_score'] = sum(weighted_scores) / sum(Config.SENTIMENT_WEIGHT.values())
            
            # Determine overall sentiment
            if sentiment_data['overall_score'] > 0.2:
                sentiment_data['overall_sentiment'] = 'bullish'
            elif sentiment_data['overall_score'] < -0.2:
                sentiment_data['overall_sentiment'] = 'bearish'
            else:
                sentiment_data['overall_sentiment'] = 'neutral'
        
        return sentiment_data
    
    def _should_update(self, source: str) -> bool:
        """Check if source should be updated based on interval."""
        if source not in self.last_update:
            return True
        
        time_diff = (datetime.now() - self.last_update[source]).total_seconds()
        return time_diff > Config.SENTIMENT_UPDATE_INTERVAL
    
    def _get_twitter_sentiment(self) -> Dict:
        """Get sentiment from Twitter/X."""
        if not self.twitter_client:
            return None
        
        try:
            # Search for BTC related tweets
            query = "BTC OR Bitcoin -is:retweet lang:en"
            tweets = self.twitter_client.search_recent_tweets(
                query=query,
                max_results=100,
                tweet_fields=['created_at', 'public_metrics']
            )
            
            if not tweets.data:
                return None
            
            # Analyze sentiment
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            
            # Simple keyword-based sentiment (would use ML model in production)
            positive_keywords = ['bullish', 'moon', 'pump', 'buy', 'long', 'up', 'green', 'ath']
            negative_keywords = ['bearish', 'dump', 'sell', 'short', 'down', 'red', 'crash']
            
            for tweet in tweets.data:
                text = tweet.text.lower()
                
                if any(keyword in text for keyword in positive_keywords):
                    positive_count += 1
                elif any(keyword in text for keyword in negative_keywords):
                    negative_count += 1
                else:
                    neutral_count += 1
            
            total = positive_count + negative_count + neutral_count
            
            sentiment_score = 0
            if total > 0:
                sentiment_score = (positive_count - negative_count) / total
            
            sentiment = 'neutral'
            if sentiment_score > 0.1:
                sentiment = 'bullish'
            elif sentiment_score < -0.1:
                sentiment = 'bearish'
            
            self.last_update['twitter'] = datetime.now()
            
            return {
                'sentiment': sentiment,
                'score': sentiment_score,
                'positive_ratio': positive_count / total if total > 0 else 0,
                'negative_ratio': negative_count / total if total > 0 else 0,
                'sample_size': total
            }
            
        except Exception as e:
            self.logger.error(f"Error getting Twitter sentiment: {e}")
            return None
    
    def _get_reddit_sentiment(self) -> Dict:
        """Get sentiment from Reddit."""
        if not self.reddit_client:
            return None
        
        try:
            # Get posts from crypto subreddits
            subreddits = ['Bitcoin', 'CryptoCurrency', 'BitcoinMarkets']
            posts = []
            
            for subreddit_name in subreddits:
                subreddit = self.reddit_client.subreddit(subreddit_name)
                posts.extend(list(subreddit.hot(limit=30)))
                posts.extend(list(subreddit.new(limit=20)))
            
            # Analyze sentiment
            positive_count = 0
            negative_count = 0
            total_score = 0
            
            for post in posts:
                # Use Reddit's upvote ratio as sentiment indicator
                upvote_ratio = post.upvote_ratio
                score = post.score
                
                # Weight by engagement
                weight = min(score / 100, 10)  # Cap weight at 10
                
                if upvote_ratio > 0.7:
                    positive_count += weight
                elif upvote_ratio < 0.3:
                    negative_count += weight
                
                total_score += (upvote_ratio - 0.5) * 2 * weight
            
            total_weight = positive_count + negative_count
            
            sentiment_score = 0
            if total_weight > 0:
                sentiment_score = total_score / total_weight
            
            sentiment = 'neutral'
            if sentiment_score > 0.1:
                sentiment = 'bullish'
            elif sentiment_score < -0.1:
                sentiment = 'bearish'
            
            self.last_update['reddit'] = datetime.now()
            
            return {
                'sentiment': sentiment,
                'score': sentiment_score,
                'sample_size': len(posts),
                'average_upvote_ratio': sum(post.upvote_ratio for post in posts) / len(posts) if posts else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting Reddit sentiment: {e}")
            return None
    
    def _get_fear_greed_index(self) -> Dict:
        """Get Fear & Greed Index."""
        try:
            response = requests.get(Config.FEAR_GREED_API, timeout=5)
            data = response.json()
            
            if 'data' not in data or not data['data']:
                return None
            
            current_value = int(data['data'][0]['value'])
            classification = data['data'][0]['value_classification']
            
            # Convert to normalized score (-1 to 1)
            normalized_score = (current_value - 50) / 50
            
            # Convert classification to sentiment
            sentiment_map = {
                'Extreme Fear': 'bearish',
                'Fear': 'bearish',
                'Neutral': 'neutral',
                'Greed': 'bullish',
                'Extreme Greed': 'bullish'
            }
            
            sentiment = sentiment_map.get(classification, 'neutral')
            
            self.last_update['fear_greed'] = datetime.now()
            
            return {
                'value': current_value,
                'classification': classification,
                'sentiment': sentiment,
                'score': normalized_score
            }
            
        except Exception as e:
            self.logger.error(f"Error getting Fear & Greed Index: {e}")
            return None
    
    def _get_news_sentiment(self) -> Dict:
        """Get sentiment from news aggregators."""
        if not Config.NEWS_API_KEY:
            return None
        
        try:
            # Get crypto news
            url = Config.NEWS_API
            params = {
                'q': 'Bitcoin OR BTC OR cryptocurrency',
                'apiKey': Config.NEWS_API_KEY,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': 50
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'articles' not in data:
                return None
            
            articles = data['articles']
            
            # Analyze headlines
            positive_count = 0
            negative_count = 0
            
            positive_keywords = ['surge', 'rally', 'gain', 'up', 'high', 'bull', 'positive', 'growth']
            negative_keywords = ['crash', 'fall', 'drop', 'down', 'low', 'bear', 'negative', 'decline']
            
            for article in articles:
                title = article.get('title', '').lower()
                description = article.get('description', '').lower()
                content = title + ' ' + description
                
                if any(keyword in content for keyword in positive_keywords):
                    positive_count += 1
                elif any(keyword in content for keyword in negative_keywords):
                    negative_count += 1
            
            total = positive_count + negative_count
            
            sentiment_score = 0
            if total > 0:
                sentiment_score = (positive_count - negative_count) / total
            
            sentiment = 'neutral'
            if sentiment_score > 0.1:
                sentiment = 'bullish'
            elif sentiment_score < -0.1:
                sentiment = 'bearish'
            
            self.last_update['news'] = datetime.now()
            
            return {
                'sentiment': sentiment,
                'score': sentiment_score,
                'articles_analyzed': len(articles),
                'positive_ratio': positive_count / total if total > 0 else 0,
                'negative_ratio': negative_count / total if total > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting news sentiment: {e}")
            return None