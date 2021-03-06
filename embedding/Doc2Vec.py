import math
import sys

import numpy as np
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split

class GensimDoc2Vec():

    def __init__(self, data_name, number_of_class, alpha=0.001, size=25, dm=0, window=8, min_count=3, epoch=200, batch_size=1000):
        print("Doc2Vec by Gensim")
        self.data_name = data_name
        self.alpha = alpha
        self.dm = dm
        self.window = window
        self.min_count = min_count
        self.size = size
        self.epoch = epoch
        self.batch_size = batch_size
        self.model = Doc2Vec(alpha=self.alpha, size=self.size, dm=self.dm, window=self.window,
                             min_count=self.min_count, workers=4, compute_loss=True, seed=12345)
        self.all_label = set(range(number_of_class))

    def tag_vector(self):
        tag_vector = []
        for i in range(len(self.all_label)):
            try:
                tag_vector.append(self.model.docvecs['class_%d' % i])
            except KeyError:
                tag_vector.append(np.zeros(self.size))
        tag_vector = np.array(tag_vector)
        return tag_vector

    def calculate_similar(self, transform_data, labels, tag_vector):
        index = np.arange(0, len(transform_data), self.batch_size).tolist()
        index.append(len(transform_data))
        same_similar = 0
        diff_similar = 0
        all_simiilar = 0
        for j in range(len(index) - 1):
            start, end = [index[j], index[j + 1]]
            batch_data = transform_data[start:end]
            batch_label = labels[start:end]
            cosine = cosine_similarity(batch_data, tag_vector)

            all_s = []
            all_d = []
            all_a = []
            for i, label in zip(range(len(batch_data)), batch_label):
                list_label = list(label)
                same = np.mean(cosine[i][list_label])
                list_not_same_label = list(self.all_label - set(label))
                diff = np.mean(cosine[i][list_not_same_label])
                alla = np.mean(cosine[i])
                if math.isnan(same):
                    same = 0
                if math.isnan(diff):
                    diff = 0
                if math.isnan(alla):
                    alla = 0
                all_s.append(same)
                all_d.append(diff)
                all_a.append(alla)
            same_similar = same_similar + \
                np.sum(np.array(all_s))
            diff_similar = diff_similar + \
                np.sum(np.array(all_d))
            all_simiilar = all_simiilar + np.sum(np.array(all_a))
        same = same_similar
        diff = (same_similar - diff_similar)
        avg_diff = (same_similar - diff_similar) / same_similar
        return same, diff, avg_diff

    def prepare_data(self, datas, labels):
        return [TaggedDocument(
            datas[i], [str(i)] + ['class_%d' % j for j in labels[i]]) for i in range(len(datas))]

    def fit(self, datas, labels, datas_validate, labels_validate, second_run=False, early_stopping=True, one_time=False):
        documents = self.prepare_data(datas, labels)
        if not second_run:
            self.model.build_vocab(documents)
        max_diff = 0
        if one_time:
            each_time = self.epoch
        else:
            each_time = int(self.epoch / 50)
            each_time = 1 if each_time == 0 else each_time
        time_before_stop = self.epoch / (each_time * 8)
        c = 0
        is_saving = False
        for i in range(int(self.epoch / each_time)):
            self.model.train(
                documents, total_examples=self.model.corpus_count, epochs=each_time)

            tag_vector = self.tag_vector()
            transform_data = self.transform(datas_validate)
            same, diff, avg_diff = self.calculate_similar(
                transform_data, labels_validate, tag_vector)
            print("Epoch: %i" %
                  ((i + 1) * each_time))
            if i >= time_before_stop:
                if max_diff < avg_diff:
                    max_diff = avg_diff
                    c = 0
                    self.model.save(
                        'export/%s/doc2vec.model' % self.data_name)
                    is_saving = True
                else:
                    c = c + 1

            if c >= 3 and early_stopping:
                # print("Stopping Similar: %.5f" % max_diff)
                if is_saving:
                    self.model = Doc2Vec.load(
                        'export/%s/doc2vec.model' % self.data_name)
                break

        return same, diff, avg_diff

    def transform(self, datas):
        return np.array([self.model.infer_vector(i) for i in datas])

    def load_model(self, file_name):
        self.model = Doc2Vec.load(file_name)
