
import os
import stats_utils
import datetime
import collections
import pandas as pd
import numpy as np

pd.set_option('display.width', 500)
pd.set_option('display.max_columns', 500)

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

from medinfo.ml.SupervisedClassifier import SupervisedClassifier

from scripts.LabTestAnalysis.machine_learning.LabNormalityPredictionPipeline \
    import NON_PANEL_TESTS_WITH_GT_500_ORDERS, STRIDE_COMPONENT_TESTS, UMICH_TOP_COMPONENTS

all_panels = NON_PANEL_TESTS_WITH_GT_500_ORDERS
all_components = STRIDE_COMPONENT_TESTS
all_UMichs = UMICH_TOP_COMPONENTS


def plot_predict_twoside_bar(lab_type="panel", wanted_PPV=0.95):
    df = pd.read_csv('data_performance_stats/best-alg-%s-summary-trainPPV.csv' % lab_type,
                     keep_default_na=False)
    df = df[df['train_PPV']==wanted_PPV]

    df['all_positive'] = df['true_positive'] + df['false_positive']
    df['all_negative'] = df['true_negative'] + df['false_negative']

    df['true_negative'] = -df['true_negative']
    df['all_negative'] = -df['all_negative']

    df['count'] = df['count'].apply(lambda x:float(x) if x!='' else 0)
    if lab_type=='component':
        df['count'] = df['count'].apply(lambda x:x/1000000)

    df['all_positive'] *= df['count']
    df['true_positive'] *= df['count']
    df['all_negative'] *= df['count']
    df['true_negative'] *= df['count']
    # print df[['true_positive', 'all_positive',
    #           'true_negative', 'all_negative']].head(5).plot(kind='barh')

    df_toplot = df.head(10)
    df_toplot.head(10)[['lab', 'PPV', 'NPV', 'sensitivity', 'specificity', 'LR_p', 'LR_n']].to_csv('predict_panel_normal_sample.csv', index=False)

    df_toplot = df_toplot.sort_values('lab', ascending=False)
    fig, ax = plt.subplots()
    ax.barh(df_toplot['lab'], df_toplot['all_positive'], color='orange', alpha=0.5, label='False Positive')
    ax.barh(df_toplot['lab'], df_toplot['true_positive'], color='blue', alpha=1, label='True Positive')

    ax.barh(df_toplot['lab'], df_toplot['all_negative'], color='blue', alpha=0.5, label='False Negative')
    ax.barh(df_toplot['lab'], df_toplot['true_negative'], color='orange', alpha=1, label='True Negative')

    for i, v in enumerate(df_toplot['all_negative']):
        ax.text(-0.15, i, df_toplot['lab'].values[i], color='k')

    plt.yticks([])
    plt.legend()
    if lab_type=='panel':
        plt.xlabel('total lab cnt in 2014-2016')
    elif lab_type=='component':
        plt.xlabel('total lab cnt (in millions) in 2014-2016')
    plt.ylabel('labs')

    plt.show()


def plot_NormalRate__bar(lab_type="panel", wanted_PPV=0.95, add_predictable=False, look_cost=False):
    '''
    Horizontal bar chart for Popular labs.
    '''

    df = pd.read_csv('data_performance_stats/best-alg-%s-summary-trainPPV.csv' % lab_type,
                     keep_default_na=False)
    df = df[df['train_PPV']==wanted_PPV]

    df = df[df['lab']!='LABNA'] # TODO: fix LABNA's price here

    df['normal_rate'] = (df['true_positive'] + df['false_negative']).round(5)

    # if lab_type == "component":
    #     df = df.rename(columns={'2016_Vol': 'count'})
    #     df = df.dropna()
    df['count'] = df['count'].apply(lambda x: 0 if x=='' else x)

    df['volumn'] = df['count'].apply(lambda x: float(x) / 1000000.) #
    volumn_label = 'Total Cnt (in millions) in 2016'

    if look_cost:
        df['volumn'] = df['volumn'] * df['mean_price'].apply(lambda x: float(x)) # cost
        volumn_label = 'Total cost in 2014-2016'

    '''
    Picking the top 20 popular labs.
    '''
    df_sorted_by_cnts = df.sort_values('volumn', ascending=False).ix[:,
                        ['lab', 'normal_rate', 'true_positive', 'volumn']].drop_duplicates().head(20).copy()
    df_sorted_by_cnts = df_sorted_by_cnts.sort_values('volumn', ascending=True)

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.barh(df_sorted_by_cnts['lab'], df_sorted_by_cnts['volumn'], color='grey', alpha=0.5,
            label=volumn_label)

    df_sorted_by_cnts['normal_volumn'] = df_sorted_by_cnts['normal_rate']*df_sorted_by_cnts['volumn']
    ax.barh(df_sorted_by_cnts['lab'], df_sorted_by_cnts['normal_volumn'],
            color='blue', alpha=0.5, label='Normal lab cost')
    # for i, v in enumerate(df_sorted_by_cnts['normal_volumn']):
    #     ax.text(v + 2, i, str("{0:.0%}".format(df_sorted_by_cnts['normal_rate'].values[i])), color='k', fontweight='bold')

    df_sorted_by_cnts['truepo_volumn'] = df_sorted_by_cnts['true_positive']*df_sorted_by_cnts['volumn']
    if add_predictable:
        ax.barh(df_sorted_by_cnts['lab'], df_sorted_by_cnts['truepo_volumn'],
                color='blue', alpha=0.9, label='True positive saving') #'True Positive@0.95 train_PPV'
        for i, v in enumerate(df_sorted_by_cnts['truepo_volumn']):
            ax.text(v, i, str("{0:.0%}".format(df_sorted_by_cnts['true_positive'].values[i])), color='k', fontweight='bold')


    # plt.xlim([0,1])
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(14)

    plt.legend()
    plt.show()

def get_waste_in_7days(lab_type='panel'):
    if lab_type == 'panel':
        all_labs = all_panels #stats_utils.get_top_labs(lab_type=lab_type, top_k=10)
    elif lab_type == 'component':
        all_labs = all_components

    res_df = pd.DataFrame()
    data_file_all = '%s_waste_in_7days.csv'%lab_type

    if not os.path.exists(data_file_all):

        import tmp

        for i, lab in enumerate(all_labs):
            data_file = '%s_Usage_2014-2016.csv'%lab

            if not os.path.exists(data_file):
                results = stats_utils.query_lab_usage__df(lab=lab,
                                                          lab_type=lab_type,
                                                          time_start='2014-01-01',
                                                          time_end='2016-12-31')
                df = pd.DataFrame(results, columns=['pat_id', 'order_time', 'result'])
                df.to_csv(data_file, index=False)
            else:
                df = pd.read_csv(data_file,keep_default_na=False)

            my_dict = {'lab':lab}
            my_dict.update(stats_utils.get_prevweek_normal__dict(df))

            print my_dict

            # my_dict = tmp.my_dictt[i]
            # print my_dict
            res_df = res_df.append(my_dict, ignore_index=True)

        max_num = len(res_df.columns)-1
        res_df = res_df[['lab'] + range(max_num)]#[str(x)+' repeats' for x in range(max_num)]]
        res_df = res_df.rename(columns={x:str(x)+' repeats' for x in range(max_num)})
        res_df.to_csv(data_file_all, index=False)
    else:
        res_df = pd.read_csv(data_file_all)

    labs_toPlot = stats_utils.get_top_labs(lab_type)
    max_repeat = 10
    for lab in labs_toPlot: #['LABLAC', 'LABLACWB', 'LABK', 'LABPHOS']:
        nums = res_df[res_df['lab']==lab].values[0][1:max_repeat+1]
        print nums
        nums_valid = [x for x in nums if x]
        print nums_valid
        plt.plot(range(len(nums_valid)), nums_valid, label=lab)

    plt.ylim([0,1])
    plt.xlabel('Num Normality in a Week')
    plt.ylabel('Normal Rate')
    plt.legend()
    plt.show()

def get_LabUsage__csv(lab_type='panel'):
    '''
    Overuse of labs figure.
    '''

    if lab_type == 'panel':
        all_labs = stats_utils.get_top_labs('panel') #stats_utils.get_top_labs(lab_type=lab_type, top_k=10)
    elif lab_type == 'component':
        all_labs = all_components
    print 'all_labs:', all_labs

    lab_ind = 0
    for lab in all_labs[::-1]:#all_labs[:10][::-1]:

        data_file = '%s_Usage_2014-2016.csv'%lab

        if not os.path.exists(data_file):
            results = stats_utils.query_lab_usage__df(lab=lab,
                                                      lab_type=lab_type,
                                                      time_start='2014-01-01',
                                                      time_end='2016-12-31')
            df = pd.DataFrame(results, columns=['pat_id', 'order_time', 'result'])
            df.to_csv(data_file, index=False)
        else:
            df = pd.read_csv(data_file,keep_default_na=False)

        if True:
            prevday_cnts_dict = stats_utils.get_prevday_cnts__dict(df)

            '''
            We only care about (0, 1 day], (1 day, 3 days], (3 days, 7 days] stats
            '''
            prevday_cnts_simple_dict = {'0 prev': prevday_cnts_dict[-1],
                                        '0-1 day': prevday_cnts_dict[0],
                                        '1-3 days': sum(prevday_cnts_dict[x] for x in range(1,4)),
                                        '3-7 days': sum(prevday_cnts_dict[x] for x in range(4,8)),
                                        'Longer': sum(prevday_cnts_dict[x] for x in range(8, 365))
                                        }
        else:
            import tmp
            prevday_cnts_simple_dict = tmp.prevday_cnts_simple_dicts[lab_ind]
        print prevday_cnts_simple_dict

        pre_sum = 0
        alphas = [1,0.5,0.4,0.3,0.2]
        for i, key in enumerate(sorted(prevday_cnts_simple_dict.keys())):

            pre_sum += prevday_cnts_simple_dict[key]

            if i > 0:
                if lab_ind == 0:
                    plt.barh([lab], pre_sum, color='b', alpha=alphas[i], label=key)
                else:
                    plt.barh([lab], pre_sum, color='b', alpha=alphas[i])
            else:
                if lab_ind == 0:
                    plt.barh([lab], pre_sum, color='b', alpha=alphas[i], label=key)
                else:
                    plt.barh([lab], pre_sum, color='b', alpha=alphas[i])
        lab_ind += 1
    plt.legend()
    plt.show()
    # quit()
    #
    # print 'total cnt:', df.shape[0]
    # print 'repetitive cnt:', sum(prevday_cnts_dict.values())
    # print 'within 24 hrs:', prevday_cnts_dict[0]
    # print 'within 48 hrs:', prevday_cnts_dict[1]

def plot_curves__subfigs(lab_type='component', curve_type="roc"):

    if lab_type == 'panel':
        data_folder = '../machine_learning/data-panels/'
        all_labs = NON_PANEL_TESTS_WITH_GT_500_ORDERS
        # df = pd.read_csv('RF_important_features_panels.csv', keep_default_na=False)
    elif lab_type == 'component':
        data_folder = '../machine_learning/data-components/'
        all_labs = STRIDE_COMPONENT_TESTS
        # df = pd.read_csv('RF_important_features_components.csv', keep_default_na=False)
    elif lab_type == 'UMich':
        data_folder = "../machine_learning/data-UMichs/"
        all_labs = UMICH_TOP_COMPONENTS

    # labs = df.sort_values('score 1', ascending=False)['lab'].values.tolist()[:15]


    num_labs_in_one_fig = 10
    col = 5
    row = num_labs_in_one_fig/col

    scores_base = []
    scores_best = []

    fig_width, fig_heights = col*3., 24./col

    plt.figure(figsize=(fig_width, fig_heights))
    for ind, lab in enumerate(all_labs):

        xVal_base, yVal_base, score_base, xVal_best, yVal_best, score_best \
            = stats_utils.get_curve_onelab(lab,
                                           all_algs=SupervisedClassifier.SUPPORTED_ALGORITHMS,
                                           data_folder=data_folder,
                                           curve_type=curve_type)
        scores_base.append(score_base)
        scores_best.append(score_best)

        # 0 -> 0, 0
        # 1 -> 0, 1
        # 2 -> 1, 0
        # 3 -> 1, 1
        ind_in_fig = ind%10
        i, j = ind_in_fig/col, ind_in_fig%col
        plt.subplot2grid((row, col), (i, j))

        plt.plot(xVal_base, yVal_base, label='%0.2f' % (score_base))
        plt.plot(xVal_best, yVal_best, label='%0.2f' % (score_best))
        plt.xticks([])
        plt.yticks([])
        plt.xlabel(lab)  # + ' ' + str(best_auc)[:4] + ' ' + str(base_auc)[:4]
        plt.legend()

        if (ind+1)%num_labs_in_one_fig == 0:
            plt.savefig('%s-%s-subfig.png'%(all_labs[ind+1-num_labs_in_one_fig],lab))
            plt.close()
            plt.figure(figsize=(fig_width, fig_heights))

    avg_base, avg_best = np.mean(scores_base), np.mean(scores_best)
    print "Average roc among %i labs: %.3f baseline, %.3f bestalg (an improvement of %.3f)."\
          %(len(scores_base), avg_base, avg_best, avg_best-avg_base)


def plot_curves__overlap(lab_type='panel', curve_type="roc"):
    if lab_type == 'panel':
        data_folder = '../machine_learning/data-panels/'
        all_labs = NON_PANEL_TESTS_WITH_GT_500_ORDERS
    elif lab_type == 'component':
        data_folder = '../machine_learning/data-components/'
        all_labs = STRIDE_COMPONENT_TESTS
    elif lab_type == 'UMich':
        data_folder = "../machine_learning/data-UMich/"
        all_labs = UMICH_TOP_COMPONENTS

    num_labs_in_one_fig = 10
    for i, lab in enumerate(all_labs):
        xVal_base, yVal_base, base_score, xVal_best, yVal_best, best_score = \
            stats_utils.get_curve_onelab(lab,
                                     all_algs=SupervisedClassifier.SUPPORTED_ALGORITHMS,
                                     data_folder=data_folder,
                                     curve_type=curve_type)
        plt.plot(xVal_base, yVal_base, label=lab+' %.2f'%base_score)

        if (i+1)%num_labs_in_one_fig == 0:
            plt.legend()
            #plt.show()
            plt.savefig('%s-%s-baseline.png'%(all_labs[i+1-num_labs_in_one_fig],lab))
            plt.close()
    plt.close()

    for i, lab in enumerate(all_labs):
        xVal_base, yVal_base, base_score, xVal_best, yVal_best, best_score = \
            stats_utils.get_curve_onelab(lab,
                                     all_algs=SupervisedClassifier.SUPPORTED_ALGORITHMS,
                                     data_folder=data_folder,
                                     curve_type=curve_type)
        plt.plot(xVal_best, yVal_best, label=lab+' %.2f'%best_score)

        if (i+1)%num_labs_in_one_fig == 0:
            plt.legend()
            #plt.show()
            plt.savefig('%s-%s-bestalg.png'%(all_labs[i+1-num_labs_in_one_fig],lab))
            plt.close()


def plot_cartoons(lab_type='panel', labs=all_panels):
    df = pd.read_csv('RF_important_features_%ss.csv'%lab_type, keep_default_na=False)
    # labs = df.sort_values('score 1', ascending=False)['lab'].values.tolist()[:15]
    # print labs


    # lab = 'WBC'
    alg = 'random-forest'

    data_folder = "../machine_learning/data-%ss/"%lab_type

    col = 3
    row = len(labs)/col
    has_left_labs = (len(labs)%col!=0)

    plt.figure(figsize=(8, 12))

    for i in range(row):
        for j in range(col):
            ind = i * col + j
            lab = labs[ind]

            df = pd.read_csv(data_folder + "%s/%s/%s-normality-prediction-%s-direct-compare-results.csv"
                             % (lab, alg, lab, alg), keep_default_na=False)
            scores_actual_0 = df.ix[df['actual'] == 0, 'predict'].values
            scores_actual_1 = df.ix[df['actual'] == 1, 'predict'].values

            df1 = pd.read_csv(data_folder + "%s/%s/%s-normality-prediction-%s-report.tab"
                              % (lab, alg, lab, alg), sep='\t', keep_default_na=False)
            auc = df1['roc_auc'].values[0]

            if not has_left_labs:
                plt.subplot2grid((row, col), (i, j))
            else:
                plt.subplot2grid((row+1, col), (i, j))
            plt.hist(scores_actual_0, bins=30, alpha=0.8, color='r', label="abnormal")
            plt.hist(scores_actual_1, bins=30, alpha=0.8, color='g', label="normal")
            plt.xlim([0, 1])
            plt.ylim([0, 500])
            plt.xticks([])
            plt.yticks([])
            plt.xlabel(lab + ', auroc=%.2f'%auc)
            # plt.legend(lab)

    # plt.xlabel("%s score for %s"%(alg,lab))
    # plt.ylabel("num episodes, auroc=%f"%auc)
    # plt.legend()
    if has_left_labs:
        i = row
        for j in range(len(labs)%col):
            ind = i * col + j
            lab = labs[ind]

            df = pd.read_csv(data_folder + "%s/%s/%s-normality-prediction-%s-direct-compare-results.csv"
                             % (lab, alg, lab, alg), keep_default_na=False)
            scores_actual_0 = df.ix[df['actual'] == 0, 'predict'].values
            scores_actual_1 = df.ix[df['actual'] == 1, 'predict'].values

            df1 = pd.read_csv(data_folder + "%s/%s/%s-normality-prediction-%s-report.tab"
                              % (lab, alg, lab, alg), sep='\t', keep_default_na=False)
            auc = df1['roc_auc'].values[0]

            if not has_left_labs:
                plt.subplot2grid((row, col), (i, j))
            else:
                plt.subplot2grid((row + 1, col), (i, j))
            plt.hist(scores_actual_0, bins=30, alpha=0.8, color='r', label="abnormal")
            plt.hist(scores_actual_1, bins=30, alpha=0.8, color='g', label="normal")
            plt.xlim([0, 1])
            plt.ylim([0, 500])
            plt.xticks([])
            plt.yticks([])
            plt.xlabel(lab)
    plt.show()

    plt.savefig('cartoons_panels.png')


def write_importantFeatures(lab_type="component"):
    all_rows = []
    num_rf_best = 0

    if lab_type == 'component':
        all_labs = STRIDE_COMPONENT_TESTS
    elif lab_type == 'panel':
        all_labs = NON_PANEL_TESTS_WITH_GT_500_ORDERS
    elif lab_type == 'UMich':
        all_labs = UMICH_TOP_COMPONENTS

    for lab in all_labs:
        df = pd.read_csv(
            '../machine_learning/data-%ss/%s/%s-normality-prediction-report.tab'
            %(lab_type,lab,lab), sep='\t', skiprows=1, keep_default_na=False)

        best_row = df['roc_auc'].values.argmax()
        if best_row == 2:
            num_rf_best += 1

        best_row = 2#df['roc_auc'].values.argmax()
        best_model = df.ix[best_row, 'model']
        best_model_split = best_model.split(',')

        #best_alg = best_model_split[0][:best_model_split[0].find('(')]
        top_1_feature = best_model_split[1][best_model_split[1].find('[')+1:].strip()
        featu1, score1 = stats_utils.split_features(top_1_feature)

        top_2_feature = best_model_split[2].strip()
        featu2, score2 = stats_utils.split_features(top_2_feature)

        top_3_feature = best_model_split[3].strip()
        featu3, score3 = stats_utils.split_features(top_3_feature)

        curr_row = [lab, featu1, score1, featu2, score2, featu3, score3]

        all_rows.append(curr_row)

    print "Total number of labs:", len(all_rows), "num of RF best:", (num_rf_best)

    result_df = pd.DataFrame(all_rows, columns=['lab', 'feature 1', 'score 1', 'feature 2', 'score 2','feature 3', 'score 3'])
    result_df.to_csv('RF_important_features_%ss.csv'%lab_type, index=False)

def print_HosmerLemeshowTest():
    labs = NON_PANEL_TESTS_WITH_GT_500_ORDERS
    alg = 'random-forest'  # 'regress-and-round' #'random-forest'

    p_vals = []

    for lab in labs:
        df_new = pd.read_csv(
            '../machine_learning/data-panels-calibration-sigmoid/%s/%s/%s-normality-prediction-%s-direct-compare-results.csv'
            % (lab, alg, lab, alg),
            keep_default_na=False)
        actual = df_new['actual'].values
        predict = df_new['predict'].values
        p_val = stats_utils.Hosmer_Lemeshow_Test(actual_labels=actual, predict_probas=predict)
        p_vals.append(p_val)

    print sorted(p_vals)

def PPV_judgement(lab_type="panel", PPV_wanted=0.95):
    df_fix_test = pd.read_csv(
        "data_performance_stats/thres_from_testPPV/best-alg-%s-summary.csv" % lab_type,
        keep_default_na=False)
    df_fix_test = df_fix_test[df_fix_test['test_PPV']==PPV_wanted]
    df_fix_test['actual_normal'] = df_fix_test['true_positive'] + df_fix_test['false_negative']
    df_fix_test['predict_normal'] = df_fix_test['true_positive'] + df_fix_test['false_positive'] #[['normal_prevalence', '']]
    df_fix_test[['lab', 'actual_normal', 'predict_normal']].sort_values('predict_normal', ascending=False).to_csv("validation_fixPPV_%ss.csv"%lab_type, index=False) #.to_string(index=False)

def PPV_guideline(lab_type="panel"):

    df_fix_train = pd.read_csv("data_performance_stats/best-alg-%s-summary-trainPPV.csv"%lab_type,
                               keep_default_na=False)

    range_bins = [0.99] + np.linspace(0.95, 0.5, num=10).tolist()
    columns = ['Target PPV', 'Total labs', 'Valid labs']
    columns += ['[0.99, 1]']
    for i in range(len(range_bins) - 1):
        columns += ['[%.2f, %.2f)' % (range_bins[i + 1], range_bins[i])]

    rows = []
    for wanted_PPV in [0.8, 0.90, 0.95, 0.99][::-1]: # TODO: what is the problem with 0.9? LABHIVWBL
        cur_row = [wanted_PPV]

        PPVs_from_train = df_fix_train.ix[df_fix_train['train_PPV']==wanted_PPV, ['PPV']]
        cur_row.append(PPVs_from_train.shape[0]) # "Total number of labs:"

        PPVs_from_train = PPVs_from_train.dropna()['PPV'].values
        PPVs_from_train = np.array([float(x) for x in PPVs_from_train if x!='']) #TODO: why?
        vaild_PPV_num = PPVs_from_train.shape[0]
        cur_row.append(vaild_PPV_num) # "Valid number of labs:"

        print "When target at PPV %.2f, the mean PPV among %i labs is %.3f, std is %.3f"\
              %(wanted_PPV, vaild_PPV_num, np.mean(PPVs_from_train), np.std(PPVs_from_train))

        cur_cnt = sum(PPVs_from_train >= 0.99)
        cur_row.append(cur_cnt)

        for i in range(len(range_bins)-1):
            cur_cnt = sum((range_bins[i+1] <= PPVs_from_train) & (PPVs_from_train < range_bins[i]))
            cur_row.append(cur_cnt)

        rows.append(cur_row)

    df = pd.DataFrame(rows, columns=columns)
    df.to_csv("predict_power_%ss.csv"%lab_type, index=False)

def check_similar_components():
    # common_labs = list(set(STRIDE_COMPONENT_TESTS) & set(UMICH_TOP_COMPONENTS))

    df_UMich = pd.read_csv('RF_important_features_UMichs.csv',keep_default_na=False)
    df_component = pd.read_csv('RF_important_features_components.csv',keep_default_na=False)

    columns_UMich_only = []
    columns_component_only = []
    for i in range(1,4):
        df_UMich = df_UMich.rename(columns={'feature %i'%i:'UMich featu %i'%i,
                                            'score %i'%i:'UMich score %i'%i})
        columns_UMich_only += ['UMich featu %i'%i, 'UMich score %i'%i]
        df_component = df_component.rename(columns={'feature %i'%i:'STRIDE featu %i'%i,
                                                    'score %i' % i:'STRIDE score %i' % i})
        columns_component_only += ['STRIDE featu %i'%i, 'STRIDE score %i'%i]

    df_combined = pd.merge(df_component, df_UMich, on='lab', how='inner')
    (df_combined[['lab'] + columns_UMich_only]).to_csv("UMich_feature_importance_to_compare.csv", index=False)
    (df_combined[['lab'] + columns_component_only]).to_csv("component_feature_importance_to_compare.csv", index=False)

def get_labs_cnts(lab_type):
    df = pd.DataFrame(columns=['lab', 'cnt 2014-2016'])

    if lab_type == 'panel':
        labs = all_panels
    elif lab_type == 'component':
        labs = all_components

    for lab in labs:
        try:
            cur_result = stats_utils.query_lab_cnts(lab=lab,
                                                    lab_type=lab_type,
                                                    time_limit=('2014-01-01', '2016-12-31'))
            print cur_result
            df = df.append({'lab': cur_result[0], 'cnt 2014-2016': cur_result[1]}, ignore_index=True)
        except Exception as e:
            print e

    df.to_csv('%s-cnts-2014-2016.csv' % lab_type, index=False)

if __name__ == '__main__':
    # plot_cartoons(lab_type='panel', labs=['LABUAPRN','LABCAI','LABPT',
    #                                       'LABUA', 'LABPTT', 'LABHEPAR',
    #                                       'LABCMVQT', 'LABURNC', 'LABPTEG'])
    # plot_cartoons('UMich', labs=UMICH_TOP_COMPONENTS)

    plot_curves__subfigs(lab_type='component', curve_type="roc")
    # plot_curves__overlap(lab_type='UMich', curve_type="roc")
    # PPV_guideline(lab_type="UMich")

    # check_similar_components()
    # write_importantFeatures(lab_type='UMich')

    # plot_NormalRate__bar(lab_type="panel", wanted_PPV=0.95, add_predictable=True, look_cost=True)
    # get_waste_in_7days('component')

    # get_LabUsage__csv('component')

    # plot_predict_twoside_bar('component')