from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pickle
from typing import List, Dict
import numpy as np
from functools import lru_cache

# Initialize FastAPI app
app = FastAPI(
    title="Movie Recommender API",
    description="ML-powered movie recommendation system",
    version="1.0.0"
)

# CORS middleware - allows React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for model
movies_df = None
similarity_matrix = None
movie_indices = {}  # Cache for faster lookups

# Load ML model and data
try:
    print("📦 Loading model...")
    movies_df = pickle.load(open('movie_list.pkl', 'rb'))
    similarity_matrix = pickle.load(open('similarity.pkl', 'rb'))
    
    # Pre-compute movie title to index mapping for faster lookups
    movie_indices = {title: idx for idx, title in enumerate(movies_df['title'])}
    
    print("✅ Model loaded successfully!")
    print(f"📊 Loaded {len(movies_df)} movies")
except FileNotFoundError as e:
    print(f"❌ Error loading model files: {e}")
    print("Make sure 'movie_list.pkl' and 'similarity.pkl' are in the same directory")

# Pydantic models for request/response
class RecommendRequest(BaseModel):
    movie_name: str

class MovieRecommendation(BaseModel):
    title: str
    similarity_score: float

class RecommendResponse(BaseModel):
    selected_movie: str
    recommendations: List[MovieRecommendation]

@lru_cache(maxsize=1000)  # Cache up to 1000 recent recommendations
def get_recommendations_cached(movie_name: str, num_recommendations: int = 5) -> tuple:
    """
    Get movie recommendations based on similarity (cached version)
    Returns tuple for hashability (required for lru_cache)
    """
    try:
        # Use pre-computed index mapping for O(1) lookup instead of O(n)
        if movie_name not in movie_indices:
            raise IndexError(f"Movie '{movie_name}' not found")
        
        movie_index = movie_indices[movie_name]
        
        # Get similarity scores for this movie (already computed)
        movie_similarities = similarity_matrix[movie_index]
        
        # Get indices of most similar movies (excluding the movie itself)
        # Using numpy for faster sorting
        similar_indices = np.argsort(movie_similarities)[::-1][1:num_recommendations + 1]
        
        # Build recommendations list
        recommendations = []
        for idx in similar_indices:
            movie_title = movies_df.iloc[idx].title
            similarity_score = float(movie_similarities[idx])  # Convert numpy float to Python float
            
            recommendations.append({
                "title": movie_title,
                "similarity_score": round(similarity_score * 100, 1)  # Convert to percentage
            })
        
        # Return as tuple for caching
        return tuple((rec["title"], rec["similarity_score"]) for rec in recommendations)
    
    except IndexError:
        raise HTTPException(
            status_code=404,
            detail=f"Movie '{movie_name}' not found in database"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating recommendations: {str(e)}"
        )

def get_recommendations(movie_name: str, num_recommendations: int = 5) -> List[Dict]:
    """
    Wrapper function to convert cached tuple back to list of dicts
    """
    cached_results = get_recommendations_cached(movie_name, num_recommendations)
    return [
        {"title": title, "similarity_score": score}
        for title, score in cached_results
    ]

# API Endpoints

@app.get("/")
async def root():
    """
    Root endpoint - API health check
    """
    return {
        "message": "Movie Recommender API is running!",
        "version": "1.0.0",
        "status": "⚡ Optimized with caching",
        "endpoints": {
            "/movies": "GET - List all movies",
            "/recommend": "POST - Get movie recommendations",
            "/docs": "API documentation"
        }
    }

@app.get("/movies")
async def get_movies():
    """
    Get list of all available movies
    """
    try:
        movie_list = movies_df['title'].tolist()
        return {
            "count": len(movie_list),
            "movies": sorted(movie_list)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching movies: {str(e)}"
        )

@app.post("/recommend", response_model=RecommendResponse)
async def recommend_movies(request: RecommendRequest):
    """
    Get movie recommendations
    
    - **movie_name**: Name of the movie to get recommendations for
    
    Returns 5 similar movies with similarity scores
    
    ⚡ Optimized with caching for faster responses!
    """
    try:
        recommendations = get_recommendations(request.movie_name)
        
        return RecommendResponse(
            selected_movie=request.movie_name,
            recommendations=recommendations
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "model_loaded": movies_df is not None and similarity_matrix is not None,
        "cache_info": {
            "hits": get_recommendations_cached.cache_info().hits,
            "misses": get_recommendations_cached.cache_info().misses,
            "size": get_recommendations_cached.cache_info().currsize
        }
    }

@app.get("/cache/clear")
async def clear_cache():
    """
    Clear the recommendation cache
    """
    get_recommendations_cached.cache_clear()
    return {
        "message": "Cache cleared successfully",
        "cache_info": get_recommendations_cached.cache_info()._asdict()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)