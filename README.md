# Artifact for Automated Testing of Software that Uses Machine Learning APIs

This artifact for our paper “Automated Testing of Software that Uses Machine Learning APIs (#158)” includes source code of our testing tool Keeper, benchmark suite, user study materials and a tool demo video. We choose to claim for the Reusable and Available badges, and we hope this artifact can motivate and help future research to further tackle ML API misuses.

The artifact has been published as [a project on Github](https://github.com/mlapistudy/ICSE2022_158).

## What's inside the artifact:

For availability and reusability, we provide source code of our tool Keeper and the instructions for setting up working environment. In addition, we provide benchmark suite, evaluation result and user study materials.

Below are details of what is included in each part:

1. Source code of Keeper, containing
   1. IDE plugin version. Located in `./ide_plugin`
   2. Main algorithm. Located in `./testing_tool`
2. Tool Demo video. Located in `./tool_demo.mp4`
3. A benchmark suite of 63 applications and their evaluation results (Section 6.2). Located in `./benchmark`, containing
   1. Software project name
   2. GitHub link
   3. Used ML API
   4. Number of branches
   5. Branch coverage of Keeper and baselines (Table 3)
   6. Failures detected by Keeper (Table 2)
   7. The affect of accuracy threshold
4. User study material (Section 6.3). Located in `./user_study`, containing
   1. A survey
   2. A consent form
   3. A survey result summary
   4. The script for processing raw data


## How to obtain paper's result from our tool?

### Software testing evaluation
Our software testing evaluation results in Section 6.2 could be found in `./benchmark` folder. These results could be obtained with `./ide_plugin` and `./testing_tool` folder. Please follow `./INSTALL.md` to set up environment and instructions in `./ide_plugin/README.md` to launch our tool Keeper.

### User study
Our user study results in Section 6.3 could be obtained from `./user_study` folder.

In `./user_study/survey_result.xlsx`, there are two tabs:

1. Result tab: Contains answer distribution of each survey questions. The cells for computation are colored with light blue: Row 28-32 shows the overal perference of each application example.
2. Explaination tab: Contains explaination of each question ID.

## What to do with the artifact and how?

One can use the code and data to check the statistic details and reproduce the experiments in our paper.

We put detailed instructions for setting up the environment in the `./INSTALL.md` file. The instructions for Keeper is in the `./ide_plugin/README.md` file.