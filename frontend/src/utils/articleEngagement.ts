const likedArticlesKey = "knowledgeHubLikedArticleIds";
const savedArticlesKey = "knowledgeHubSavedArticleIds";

function readArticleIds(key: string) {
  try {
    const value = window.localStorage.getItem(key);
    return new Set(value ? JSON.parse(value) as string[] : []);
  } catch {
    return new Set<string>();
  }
}

function writeArticleIds(key: string, articleIds: Set<string>) {
  window.localStorage.setItem(key, JSON.stringify(Array.from(articleIds)));
}

function toggleArticleId(key: string, articleId: string) {
  const articleIds = readArticleIds(key);

  if (articleIds.has(articleId)) articleIds.delete(articleId);
  else articleIds.add(articleId);

  writeArticleIds(key, articleIds);
  return articleIds;
}

export function getLikedArticleIds() {
  return readArticleIds(likedArticlesKey);
}

export function toggleLikedArticle(articleId: string) {
  return toggleArticleId(likedArticlesKey, articleId);
}

export function getSavedArticleIds() {
  return readArticleIds(savedArticlesKey);
}

export function toggleSavedArticle(articleId: string) {
  return toggleArticleId(savedArticlesKey, articleId);
}

export const articleEngagementStorageKeys = {
  liked: likedArticlesKey,
  saved: savedArticlesKey,
};
