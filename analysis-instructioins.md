Using the exported data in the exported_data folder, I want you to generate an r markdown file that allows me to analyze the data as follows:

1) Create a new csv hthat merges the two csv files into one. It should essentially look like the survey_data.csv file, but include the 70 face judgements for each participant in 70 new columns, labeled with the face number. There are 60 unique faces, and 10 repeats, so for each participant, when the 10 faces are repeated, indicate in that column that it is a repeat.

2) Next, filter the data frame for only participants 7 8 9 and 10
3) Create a new column matching participant id to name: spencer 7 anthony 8 jacob 9 maya 10
4) For each participant, I want to compute the first quartile, median, and 3rd quartile rated face. So this would entail ordering the face judgements and finding the 15th, 30th, and 45th ranked faces (disregard the repeats for now, they will be used for within-rater reliability test)
5) I have supplied a csv called PetersonFaceData.csv. It contains the corresponding age for each of the face stimuli. Create a new csv that for each particpant, contains their 15th 30th and 45th ranked faces and the corresponding age
6) test within-participant reliability by doing a pearson correlation for each of the 10 repeat faces
7) note reverse-scored questions in the survey section:
    i. 3, 9, and 12 for work habits
    ii. 6 & 11 for creative perceptions
8) Compute an average score for each of the 3 surveys (kai, creative perceptions, work habits) based off each scale (indicate what it is out of in the column title)
9) These scores will then be correlated with each participants quartile rating ages. For example, I will want a test done to see if higher creative perceptions are linked to the first quartile face being younger. In total, there should be 9 tests