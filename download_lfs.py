import requests
import os

def download_lfs_file(repo_owner, repo_name, file_path, branch='main'):
    """Download LFS file from GitHub"""
    # GitHub raw content URL
    url = f"https://github.com/{repo_owner}/{repo_name}/raw/{branch}/{file_path}"
    
    print(f"Downloading {file_path}...")
    response = requests.get(url, allow_redirects=True)
    
    if response.status_code == 200:
        with open(file_path, 'wb') as f:
            f.write(response.content)
        print(f"✓ Downloaded {file_path}")
    else:
        print(f"✗ Failed to download {file_path}: {response.status_code}")
        raise Exception(f"Failed to download {file_path}")

if __name__ == "__main__":
    # Update these with your GitHub info
    REPO_OWNER = "Aech0"
    REPO_NAME = "movie-recommender-backend"
    BRANCH = "main"
    
    # Download the LFS files
    download_lfs_file(REPO_OWNER, REPO_NAME, "movie_list.pkl", BRANCH)
    download_lfs_file(REPO_OWNER, REPO_NAME, "similarity.pkl", BRANCH)
    
    print("All LFS files downloaded successfully!")
