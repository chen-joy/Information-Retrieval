from whoosh.scoring import BM25F
import math

class CustomScorer(BM25F):
    def __init__(self, B=0.75, K1=1.2):
        super().__init__(B=B, K1=K1)

    def score(self, searcher, fieldname, text, matcher):
        stats = self._get_basic_stats(searcher, fieldname, text)
        tf = matcher.weight
        return self.bm25(stats.avgdl, stats.M, stats.df, stats.field_length, tf)
    
    def bm25(self, avgdl, M, df, field_length, tf):
        idf = math.log((M - df + 0.5) / (df + 0.5 + 1))  # 修正IDF公式
        numer = tf * (self.K1 + 1)
        denom = tf + self.K1 * (1 - self.B + self.B * field_length / avgdl)
        return idf * numer / denom