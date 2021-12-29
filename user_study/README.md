# README

This folder contains material and aggreated result of our user study.

We conduct an survey to understand where bugs detected by our tool really affect software quality from end-user's perspective.  

### Material

The survey includes 4 applications from our benchmark suites, each containing an *original* version and a *fixed* version.  The applications and their two versions are shown in random order to reduce potential bias.

The online version of survey is at [here](https://uchicago.co1.qualtrics.com/jfe/form/SV_3NS7gNYHkmzRXIG). The preview of survey is available at `./survey_preview.pdf`. Consent form is available at `./consent_form.pdf`

### Result

Due to IRB restriction, we only include the aggreated result of 100 participants at `./survey_result.xlsx`. It is obtained by applying `./parse_survey.py` to survey raw data. The question ID refers to following questions:


| Question ID | Meaning                                                      |
| ----------- | ------------------------------------------------------------ |
| Q*-0        | Individual preference of each test case                      |
| Q*-1        | Which one has a higher recall? (Q3-1 asks about emotion matching of input  and output) |
| Q*-2        | How important is recall?                                     |
| Q*-3        | Which one has a higher precision?                            |
| Q*-4        | How important is precision?                                  |
| Q*-5        | Overall preference of entire software                        |

Q3 (Smart diary) recognizes emotion of the uploaded diary entry, which is a more complex question than answering T/F. So it do not have precision/recall. Instead, it asks about matching between the emotion in the response and the emotion in the uploaded diary entry.
