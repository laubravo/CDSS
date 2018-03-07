#!/usr/bin/python
"""
Utility class for analyzing the performance of a pre-trained classifier
on a set of test data.
"""

import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams
from pandas import DataFrame
import sys

from sklearn.metrics import recall_score, precision_score, f1_score
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.metrics import precision_recall_curve, roc_curve

from medinfo.ml.PredictorAnalyzer import PredictorAnalyzer
from medinfo.common.Util import log

class ClassifierAnalyzer(PredictorAnalyzer):
    ACCURACY_SCORE = 'accuracy'
    RECALL_SCORE = 'recall'
    PRECISION_SCORE = 'precision'
    F1_SCORE = 'f1'
    AVERAGE_PRECISION_SCORE = 'average_precision'
    ROC_AUC_SCORE = 'roc_auc'
    PRECISION_AT_K_SCORE = 'precision_at_k'
    K_99_PRECISION_SCORE = 'k(precision=0.99)'
    K_95_PRECISION_SCORE = 'k(precision=0.95)'
    K_90_PRECISION_SCORE = 'k(precision=0.90)'
    PERCENT_PREDICTABLY_POSITIVE = 'percent_predictably_positive'
    SUPPORTED_SCORES = [ACCURACY_SCORE, RECALL_SCORE, PRECISION_SCORE,
                        F1_SCORE, AVERAGE_PRECISION_SCORE,
                        PERCENT_PREDICTABLY_POSITIVE,
                        PRECISION_AT_K_SCORE, K_99_PRECISION_SCORE,
                        K_95_PRECISION_SCORE, K_90_PRECISION_SCORE,
                        ROC_AUC_SCORE]

    def __init__(self, classifier, X_test, y_test):
        # TODO(sbala): Make this API more flexible, so that it can work
        # with multi-label classifiers or binary classifiers whose
        # positive label != 1.
        PredictorAnalyzer.__init__(self, classifier, X_test, y_test)
        # If there is only one class in y_test, abort.
        classes = y_test[y_test.columns.values[0]].value_counts().index.values
        if len(classes) <= 1:
            sole_class = classes[0]
            log.debug('y_test only has samples of 1 class: %s' % sole_class)
            sys.exit('[ERROR] ClassifierAnalyzer: y_test only has samples of 1 class: %s' % sole_class)

        self._y_pred_prob = DataFrame(classifier.predict_probability(X_test)[:,1])
        log.debug('y_pred_prob[0].value_counts(): %s' % self._y_pred_prob[0].value_counts())

    def _score_accuracy(self):
        return PredictorAnalyzer._score_accuracy(self)

    def _score_recall(self):
        return recall_score(self._y_test, self._y_predicted)

    def _score_precision(self):
        return precision_score(self._y_test, self._y_predicted)

    def _score_f1(self):
        return f1_score(self._y_test, self._y_predicted)

    def _score_average_precision(self):
        return average_precision_score(self._y_test, self._y_pred_prob)

    def _score_roc_auc(self):
        return roc_auc_score(self._y_test, self._y_pred_prob)

    def _score_precision_at_k(self, k):
        # Get the name of the column in y_pred_prob.
        prob_col_name = self._y_pred_prob.columns.values[0]
        # Sort y_pred_prob by the values in that column.
        prob_sorted = self._y_pred_prob.sort_values(prob_col_name, ascending=False)
        # Fetch the index for pred_sort.
        prob_sorted_index = prob_sorted.index
        # Sort y_test and y_pred by that index.
        true_sorted = self._y_test.reindex(index=prob_sorted_index)
        pred_sorted = self._y_predicted.reindex(index=prob_sorted_index)
        # Fetch the top k predictions.
        pred_sorted_at_k = pred_sorted[0:k]
        true_sorted_at_k = true_sorted[0:k]
        # Return precision at k.
        return precision_score(true_sorted_at_k, pred_sorted_at_k)

    def _score_k_percentile_precision(self, desired_precision):
        k_vals, precision_vals = self.compute_precision_at_k_curve()

        # Search for k_val for which precision == precision.
        threshold_k = k_vals[0]
        for precision, k in zip(precision_vals, k_vals):
            if precision >= desired_precision:
                threshold_k = k

        return float(threshold_k) / float(len(k_vals))

    def _score_percent_predictably_positive(self, desired_precision):
        # Get the name of the column in y_pred_prob.
        prob_col_name = self._y_pred_prob.columns.values[0]
        # Sort y_pred_prob by the values in that column.
        prob_sorted = self._y_pred_prob.sort_values(prob_col_name, ascending=False)
        # Fetch the index for pred_sort.
        prob_sorted_index = prob_sorted.index
        # Sort y_test and y_pred by that index.
        true_sorted = self._y_test.reindex(index=prob_sorted_index)
        pred_sorted = self._y_predicted.reindex(index=prob_sorted_index)

        num_true_positive = 0
        num_samples = len(true_sorted.index)
        for k in range(1, num_samples):
            # Fetch the top k predictions.
            pred_sorted_at_k = pred_sorted[0:k]
            true_sorted_at_k = true_sorted[0:k]
            # Get precision at k.x
            precision_at_k = precision_score(true_sorted_at_k, pred_sorted_at_k)
            log.debug('precision_at_k: %s' % precision_at_k)
            if precision_at_k >= desired_precision:
                num_true_positive = true_sorted_at_k[true_sorted_at_k.columns.values[0]].value_counts()[1]

        return float(num_true_positive) / float(num_samples)

    def score(self, metric=None, k=None):
        if metric is None:
            metric = ClassifierAnalyzer.ACCURACY_SCORE

        if metric not in ClassifierAnalyzer.SUPPORTED_SCORES:
            raise ValueError('Score metric %s not supported.' % metric)

        if metric == ClassifierAnalyzer.ACCURACY_SCORE:
            return self._score_accuracy()
        elif metric == ClassifierAnalyzer.RECALL_SCORE:
            return self._score_recall()
        elif metric == ClassifierAnalyzer.PRECISION_SCORE:
            return self._score_precision()
        elif metric == ClassifierAnalyzer.F1_SCORE:
            return self._score_f1()
        elif metric == ClassifierAnalyzer.AVERAGE_PRECISION_SCORE:
            return self._score_average_precision()
        elif metric == ClassifierAnalyzer.ROC_AUC_SCORE:
            return self._score_roc_auc()
        elif metric == ClassifierAnalyzer.K_90_PRECISION_SCORE:
            return self._score_k_percentile_precision(0.9)
        elif metric == ClassifierAnalyzer.K_95_PRECISION_SCORE:
            return self._score_k_percentile_precision(0.95)
        elif metric == ClassifierAnalyzer.K_99_PRECISION_SCORE:
            return self._score_k_percentile_precision(0.99)
        elif metric == ClassifierAnalyzer.PERCENT_PREDICTABLY_POSITIVE:
            return self._score_percent_predictably_positive(0.99)
        elif metric == ClassifierAnalyzer.PRECISION_AT_K_SCORE:
            if k is None:
                raise ValueError('Must specify k for PRECISION_AT_K_SCORE.')
            else:
                return self._score_precision_at_k(k)

    def compute_precision_recall_curve(self):
        return precision_recall_curve(self._y_test, self._y_pred_prob)

    def plot_precision_recall_curve(self, title, dest_path):
        # Compute inputs.
        precisions, recalls, thresholds = self.compute_precision_recall_curve()
        average_precision = self._score_average_precision()

        # Set figure settings.
        rcParams['font.family'] = 'sans-serif'
        rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'Tahoma']

        # Make plot.
        plt.figure()
        plt.step(recalls, precisions, color='b', alpha=0.2, where='post')
        plt.fill_between(recalls, precisions, step='post', alpha=0.2, color='b')

        # Label axes.
        plt.xlabel('Recall')
        plt.ylabel('Precision')
        plt.ylim([0.0, 1.05])
        plt.xlim([0.0, 1.0])

        # Set title.
        plt.title('{0}: AP={1:0.2f}'.format(title, average_precision))

        # Save figure.
        plt.savefig(dest_path)
        plt.close()

    def compute_roc_curve(self):
        return roc_curve(self._y_test, self._y_pred_prob)

    def plot_roc_curve(self, title, dest_path):
        # Compute inputs.
        fprs, tprs, thresholds = self.compute_roc_curve()
        roc_auc = self._score_roc_auc()

        # Set figure settings.
        rcParams['font.family'] = 'sans-serif'
        rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'Tahoma']

        # Make plot.
        plt.figure()
        plt.plot(fprs, tprs, color='darkorange', lw=2)
        plt.plot([0, 1], [0, 1], color='gray', lw=2, linestyle='--')

        # Label axes.
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')

        # Set title.
        plt.title('%s (AUC = %s)' % (title, roc_auc))

        # Save figure.
        plt.savefig(dest_path)
        plt.close()

    def compute_precision_at_k_curve(self):
        num_samples = self._y_test.shape[0]
        k_vals = range(1, num_samples + 1)
        precision_vals = list()
        for k in k_vals:
            precision = self._score_precision_at_k(k)
            precision_vals.append(precision)

        return k_vals, precision_vals

    def plot_precision_at_k_curve(self, title, dest_path):
        # Compute inputs.
        k_vals, precision_vals = self.compute_precision_at_k_curve()

        # Set figure settings.
        rcParams['font.family'] = 'sans-serif'
        rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'Tahoma']

        # Make plot.
        plt.figure()
        plt.plot(k_vals, precision_vals, color='darkorange', lw=2)

        # Label axes.
        plt.xlabel('k')
        plt.ylabel('Precision')
        plt.ylim([0.0, 1.05])
        plt.xlim([0.0, k_vals[-1]])

        # Set title.
        plt.title('{0}'.format(title))

        # Save figure.
        plt.savefig(dest_path)
        plt.close()

    def build_report(self):
        column_names = ['model', 'test_size']
        report_dict = {
            'model': [self._predictor.description()],
            'test_size': [self._y_test.shape[0]]
        }

        # Add train and test counts.
        y_test_counts = self._y_test[self._y_test.columns[0]].value_counts()
        report_dict.update({'y_test.value_counts()': [str(y_test_counts.to_dict())]})
        column_names.append('y_test.value_counts()')

        # Add scores.
        for score_metric in ClassifierAnalyzer.SUPPORTED_SCORES:
            if score_metric == ClassifierAnalyzer.PRECISION_AT_K_SCORE:
                k_10_percent = int(0.1 * self._y_test.shape[0])
                score_label = 'precision_at_10_percent'
                score_value = self.score(score_metric, k_10_percent)
            else:
                score_label = score_metric
                score_value = self.score(metric=score_metric)
            column_names.append(score_label)
            report_dict.update({score_label: score_value})

        # Add hyperparams.
        report_dict.update({'hyperparams': str(self._predictor.hyperparams())})
        column_names.append('hyperparams')

        return DataFrame(report_dict, columns=column_names), column_names

    def write_report(self, dest_path):
        report, column_names = self.build_report()

        PredictorAnalyzer.write_report(self, report, dest_path, column_names)
