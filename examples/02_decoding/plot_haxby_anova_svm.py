"""
Decoding with ANOVA + SVM: face vs house in the Haxby dataset
===============================================================

This example does a simple but efficient decoding on the Haxby dataset:
using a feature selection, followed by an SVM.

"""

#############################################################################
# Retrieve the files of the Haxby dataset
from nilearn import datasets

# By default 2nd subject will be fetched
haxby_dataset = datasets.fetch_haxby()

# print basic information on the dataset
print('Mask nifti image (3D) is located at: %s' % haxby_dataset.mask)
print('Functional nifti image (4D) is located at: %s' %
      haxby_dataset.func[0])

#############################################################################
# Load the behavioral data
import numpy as np
labels = np.recfromcsv(haxby_dataset.session_target[0], delimiter=" ")
y = labels['labels']
session = labels['chunks']

# Restrict to faces and houses
condition_mask = np.logical_or(y == b'face', y == b'house')
y = y[condition_mask]

# We have 2 conditions
n_conditions = np.size(np.unique(y))

#############################################################################
# Prepare the fMRI data: smooth and apply the mask
from nilearn.input_data import NiftiMasker

mask_filename = haxby_dataset.mask

# For decoding, standardizing is often very important
# note that we are also smoothing the data
masker = NiftiMasker(mask_img=mask_filename, sessions=session,
                     smoothing_fwhm=4, standardize=True,
                     memory="nilearn_cache", memory_level=1)
func_filename = haxby_dataset.func[0]
X = masker.fit_transform(func_filename)
# Apply our condition_mask
X = X[condition_mask]
session = session[condition_mask]

#############################################################################
# Build the decoder

# Define the prediction function to be used.
# Here we use a Support Vector Classification, with a linear kernel
from sklearn.svm import SVC
svc = SVC(kernel='linear')

# Define the dimension reduction to be used.
# Here we use a classical univariate feature selection based on F-test,
# namely Anova. We set the number of features to be selected to 500
from sklearn.feature_selection import SelectKBest, f_classif
feature_selection = SelectKBest(f_classif, k=500)

# We have our classifier (SVC), our feature selection (SelectKBest), and now,
# we can plug them together in a *pipeline* that performs the two operations
# successively:
from sklearn.pipeline import Pipeline
anova_svc = Pipeline([('anova', feature_selection), ('svc', svc)])

#############################################################################
# Fit the decoder and predict

anova_svc.fit(X, y)
y_pred = anova_svc.predict(X)

#############################################################################
# Obtain prediction scores via cross validation

from sklearn.cross_validation import LeaveOneLabelOut, cross_val_score

# Define the cross-validation scheme used for validation.
# Here we use a LeaveOneLabelOut cross-validation on the session label
# divided by 2, which corresponds to a leave-two-session-out
cv = LeaveOneLabelOut(session // 2)

# Compute the prediction accuracy for the different folds (i.e. session)
cv_scores = cross_val_score(anova_svc, X, y)

# Return the corresponding mean prediction accuracy
classification_accuracy = np.mean(cv_scores)

# Print the results
print("Classification accuracy: %.4f / Chance level: %f" %
      (classification_accuracy, 1. / n_conditions))
# Classification accuracy: 0.9861 / Chance level: 0.5000


#############################################################################
# Visualize the results

# Look at the SVC's discriminating weights
coef = svc.coef_
# reverse feature selection
coef = feature_selection.inverse_transform(coef)
# reverse masking
weight_img = masker.inverse_transform(coef)


# USe the mean image as a background to avoid relying on anatomic data
from nilearn import image
mean_img = image.mean_img(func_filename)

# Create the figure
from nilearn.plotting import plot_stat_map, show
plot_stat_map(weight_img, mean_img, title='SVM weights')

# Saving the results as a Nifti file may also be important
weight_img.to_filename('haxby_face_vs_house.nii')


show()
