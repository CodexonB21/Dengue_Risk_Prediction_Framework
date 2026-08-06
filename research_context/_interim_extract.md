_Extracted from interim draft. Paragraphs with text: 427. Tables: 4._

Interim Report

Level 4

A Residual Compensation Modeling Framework for Dengue Risk Prediction

by Team Codexon

Faculty of Information Technology University of Moratuwa

2026

Interim Report

Level 4

A Residual Compensation Modeling Framework for Dengue Risk Prediction

by Team Codexon

Supervisor’s Name				Signature

Dr. M.F.M. Firdhous	………………………

Mrs. K.A. Dilini T. Kulawansa	………………………

Faculty of Information Technology University of Moratuwa

2026

Abstract

Dengue fever is one of the most critical challenges of the public health in tropical areas such as Sri Lanka, which are characterized by complicated seasonal patterns and changes due to the fluctuating climatic conditions, rapid urbanization processes and movement of human beings. Although there are traditional models of vector control and epidemiological forecasting, they tend to be ineffective in the face of unpredictable outbreaks due to non-linear environmental dynamics. This study hypothesizes a Residual Compensation Modeling Framework that aims at improving the accuracy of dengue risk prediction by seeking to address shortcomings of classical forecasting models. The study involves using a multi-stage analytical process: (1) establishing a baseline predictive model by using past epidemiological and climatic data, (2) applying a residual analysis to identify systematic error in original predictions, and (3) using a compensation layer to adjust against such deviations. The current interim report shows the advancements in the first phase of system design and pre-processing of data, which includes integration of microclimatic variables and region-dependent factors, which are specific to hotspots of Sri Lanka. Early findings suggest that this framework can more effectively represent the complexities of disease emergence than individual linear models. Future development will be centered on the full scale implementation of the compensation algorithm and its implementation into a user-friendly dashboard in the real-world application of the compensation algorithm to public health intervention.

Keywords: Dengue Risk Prediction, Residual Compensation Modeling, Machine Learning, Sri Lanka, Epidemiological Forecasting.

List of Figures

Figure 1: End-to-End Process of the System	36

Figure 2 : Top Level Architecture of the Proposed System	40

Figure 3: Module 1: Hybrid Time-Series Case Forecasting	40

Figure 4 : Module 2: Hybrid Outbreak Risk Classification	41

Figure 5 : Module 3: Hybrid Spatial Risk Mapping & Hotspot Detection	42

List of Tables

Table 1 : Comparison of Dengue Risk Modeling Approaches	23

Table 2: NASA POWER Meteorological Parameters Retrieved	45

Table 3: Summary of Datasets Incorporated	46

# CHAPTER 1 – INTRODUCTION

## 1.1 Introduction

The diseases that are carried by the mosquitoes especially the Dengue and the Chikungunya are a great threat to the health of the global population placing a very heavy burden to the economy of the tropical and subtropical nations. In countries such as Sri Lanka, the diseases have complicated seasonal patterns that are influenced by the climatic conditions, urbanization, as well as human movements and thus they tend to cause blistering and unpredictable outbreaks. Although there is an existence of vector control programs, the classical method of disease management has been more of a response to outbreaks, when the number of cases has reached a new peak, but not preventive. It is a common assumption that this delay in the response is explained by the absence of accurate real-time intelligence capable of forecasting the risks on a granular level. As highlighted by Uduwanage et al. (2025), the complexity of disease transmission necessitates advanced predictive models that go beyond simple historical averages to effectively anticipate outbreaks [1].

This project aims at creating an all-inclusive Disease Risk Forecasting and Alert Visualization System that combines time-series forecasting, outbreak risk categorization, and spatial hotspots mapping. This study concentrates on fine-scale predictive modeling, unlike on the traditional systems which operate on a district level to identify the risks. The system will ensure that health authorities have a real-time Command Center to visualize risks and actively deploy resources to prevent the spread of an epidemic by combining meteorological data (temperature, rainfall, humidity) with the historical disease incidence.

## 1.2 Background and Motivation

This study was conducted because of the increasing intricacy in controlling the diseases transmitted by the mosquitoes, and it is quickly getting compounded by global climate change. In tropical and subtropical areas, the epidemiology of such infections as Dengue is no longer following foreseeable historical trends. Rather, they are becoming more motivated by unstable environmental factors. To be more specific, the mosquito breeding cycles and biting habits can change incredibly with the changes in microclimates, i.e., localized changes in ambient temperature, alteration of humidity rates, or an unpredictable pattern of rainfalls within a certain city area.

A critical gap in the existing dengue prediction literature is the absence of residual compensation frameworks. Most published models, whether SARIMA, Random Forest, XGBoost, or LSTM, operate as standalone single-stage systems and do not analyze or correct their own prediction errors [5][6]. These residual errors frequently contain exploitable patterns linked to climate variability, seasonal anomalies, and demographic factors. Ignoring these residual patterns leads to systematic inaccuracies that reduce the reliability of early warning systems.

Furthermore, a notable disconnect exists between academic dengue modelling and practical decision-support tools for public health officers. As observed by Yi et al. (2023), sophisticated models rarely translate into interactive, actionable dashboards that allow field-level responders to monitor risks in real time [3]. Current government dashboards tend to be static and lack dynamic alerts or real-time interactivity [4]. This project aims to bridge both gaps, methodological and operational, by proposing a unified residual compensation framework alongside a visualization dashboard that converts model outputs into timely, interpretable risk information.

## 1.3 Problem in Brief

Although there are programs of controlling vectors, there are three challenges, which pose a significant threat to effective handling of the epidemics of Dengue:

The first challenge is the spatial distortion between prediction and reality. Most existing forecasting models operate at macro-level (district or provincial), yet mosquito breeding and disease transmission occur in more localised patterns. A district-wide response is often too broad, making it logistically and economically inefficient for targeted interventions.

Multidimensional perspective on the threat is necessary to better manage diseases, but existing systems tend to be one-dimensional. Health officials must be aware of three different metrics at the same time in order to make wise choices:

Quantitative Magnitude: The number of cases that are anticipated within the next few weeks (Forecasting).

Probabilistic Risk: The risk of the present situation developing into a full-scale outbreak (Classification).

Geographic Focus: The precise geographical area in which the risk is focused (Spatial Mapping). The majority of the systems available currently offer only one of these measures, which puts decision-makers at a disadvantage of having a partial picture of the epidemiological situation.

Despite the data being present, it tends to be missing the required mechanisms of giving early warnings to trigger immediate action. According to Uelmen Jr. et al. (2023), the interface in which the data is offered is just as important as data itself. It requires user friendly web interfaces that will enable effective real-time monitoring. However, most of the current government dashboards are based on stagnant reports or inactive maps that cannot enable the officials to filter data and simulate scenarios [4].

There is an important gap in research in the absence of a single platform that effectively integrates Regression (to forecast the number of cases), Classification (to identify the risk levels), and Spatial Analysis (to produce heatmaps) into a single, fully automated pipeline. This project will deal with this fragmentation by allocating separate yet complementary AI modeling tasks to three researchers whereby the result of such a choice would provide a comprehensive solution to all the elements of managing the risk of disease.

## 1.4 Proposed Solution

The proposed solution is a Residual Compensation Modeling Framework for dengue risk prediction. In order to have a clear and justifiable project scope, the system is designed with three complementary analytical modules, each following the same two-stage sequential pattern: a baseline model followed by a residual compensation model.

The first module is centred on short-term case prediction. It employs a SARIMA/SARIMAX baseline model using historical weekly dengue cases to generate initial forecasts that capture trend, seasonality, and autocorrelation [5]. A second-stage residual compensation model (Random Forest or XGBoost) then learns the prediction errors using lagged rainfall, temperature, humidity and other signals. The final forecast is obtained by adding the compensated residual to the baseline prediction.

The second module aims to approximate the likelihood of an outbreak instead of the actual rate of cases. It uses a baseline classifier (Random Forest or XGBoost) with lagged case counts and trend features to produce initial outbreak probabilities for both dengue. A compensation model then adjusts these probabilities using environmental anomalies and seasonal indicators. This probabilistic approach supports intuitive risk-level alerts (low/medium/high), which are aligned with risk clustering and outbreak warning frameworks [7].

The third module focuses on the spatial aspect of disease risk and the location of high-risk areas. It applies Kernel Density Estimation (KDE) and Moran’s I as the baseline spatial model on historical case locations. A spatial adjustment model then compensates for residuals using rainfall, elevation, temperature, population density and other environmental factors. The resulting risk map highlights hotspots not captured by temporal data alone. This component is designed based on the principles laid out in recent research in remote sensing and spatial epidemiology [8].

These three analytical modules produce their outputs that are incorporated into a centralized early warning system. In cases where the number of predicted cases surpasses preset limits or outbreak risk is elevated, the system automatically creates visual alerts on an interactive dashboard. This integration ensures that the complicated model outputs are converted into understandable actionable information that will inform timely and knowledgeable decision-making among public health authorities.

## 1.5 Aim and Objectives

This section outlines the overall aim and specific objectives of the proposed Residual

Compensation Modeling Framework for dengue risk prediction.

### 1.5.1 Aim

To develop a Residual Compensation Modeling Framework for dengue risk prediction that improves time-series forecasting, outbreak classification, and spatial hotspot detection by correcting baseline model errors using environmental and contextual factors.

### 1.5.2 Objectives

In order to achieve the above-mentioned aim, the following objectives have been defined:

To develop a residual compensation-based time-series forecasting model that predicts weekly dengue case counts by combining a baseline SARIMA model with climate-driven error correction.

To develop a residual compensation-based outbreak risk classification model that improves prediction accuracy by correcting baseline classification outputs using environmental anomaly indicators.

To develop a residual compensation-based spatial hotspot detection model that enhances dengue risk mapping by integrating spatial statistical techniques with environmental and demographic corrections.

## 1.5 Summary

In Chapter 1, the necessity to adopt a more granular and proactive approach to the management of mosquito-borne diseases, in this case, Dengue, in the Sri Lankan context was established. Although the current systems offer a high level of district-level data, it does not provide the accuracy and real-time interactivity demanded by effective localized intervention. The background and motivation point out a serious methodological gap: the lack of a residual compensation scheme in existing forecasting models, which tend to introduce systematic errors in their outcomes due to unaccounted environmental anomalies. The problem is defined in three perspectives, including, but not limited to, spatial distortion in macro-level predictions, the absence of a multidimensional perspective (integrating magnitude, risk, and geography), and the disconnect between complex academic modeling and practical tools of public health. In order to overcome these issues, this study presents a Residual Compensation Modeling Framework. This unified solution is comprised of three specialized modules- Short-term Case Prediction, Probabilistic Outbreak Classification, and Spatial Hotspot Mapping- each using a distinct unique two-stage sequential pattern to fix baseline errors using environmental and demographic variables. Finally, this chapter prepares a system that will convert multi-layered AI modeling into a centralized and interactive early warning dashboard to the public health authorities.

# CHAPTER 2 – LITERATURE REVIEW

## 2.1 Introduction

Dengue fever is one of the most rapidly spreading mosquito-borne diseases in tropical and subtropical countries, and is a serious and escalating public health problem. The World Health Organization estimates that there are around 390 million infections every year, with more than 100 countries experiencing endemic transmission [1]. Dengue is now hyper-endemic in Sri Lanka with complex seasonal and spatial patterns with climatic variability (rainfall, temperature, humidity), rapid urbanisation, human mobility and micro climatic conditions. Existing surveillance systems, which are mostly reactive and are based on the reporting of old cases at district or provincial level, have been found to be ineffective in timely intervention. Often these systems are not able to give granular and forward looking intelligence, which leads to delayed responses or after outbreak has already risen[1], [6].

Dengue risk management will need to rely on three important dimensions: (1) quantitative magnitude forecasting (forecasting the number of cases during the coming weeks); (2) outbreak risk classification (assessing the probability of an imminent outbreak); and (3) spatial hotspot detection (identifying the precise geographic area of high risk). To date, most research and operational systems focus on just one or two of these dimensions.  [3], [4] An important methodological shortcoming in research is the under use of residual compensation frameworks, which involve a first-stage model (statistical or machine learning) and a second-stage model that explicitly models and corrects systematic prediction errors in terms of environmental, climatic and contextual factors. [12]

This chapter provides an overview of the literature available regarding the epidemiology of dengue in the region of Sri Lanka and also in similar settings, sources of data for the study, and the three main methodological streams corresponding to the project modules. It covers traditional statistical time-series models, machine learning based techniques, hybrid and residual based techniques, classification methods, spatial statistical and GIS based techniques, early warning dashboards and evaluation practices. The strengths, limitations and gaps that drive the proposed Residual Compensation Modeling Framework are highlighted.

## 2.2 Related Work

With the rising burden of dengue in tropical and subtropical countries, literature regarding the prediction and risk modelling of dengue has been growing significantly in recent years. Existing research can be summarised into six types of analyses: epidemiological studies that analyse risk factors, data-driven feature engineering methods, statistical time-series forecasting, machine learning prediction and classification methods, spatial hotspot detection, and operational early warning systems. Progress has been made in each of these elements, but there are few models that achieve all three (probabilistic diagnostics, quantitative forecasting and geographical risk mapping all through residual compensation). This section summarises some of the main contributions in these areas, identifying methodological strengths, weaknesses and gaps to be addressed by the proposed Residual Compensation Modeling Framework.

### 2.2.1 Dengue Epidemiology and Risk Factors in Sri Lanka

Dengue fever is now a serious health problem in Sri Lanka and outbreaks occur frequently causing a heavy burden on the health care system and national economy. After the late 1980s and particularly in 2009, there has been a dramatic increase in dengue cases in the country with more than 186,000 reported cases in 2017. The Western Province, and especially Colombo, Gampaha and Kalutara Districts, have consistently been the leading areas of the country with regard to the number of cases reported, where there is a high population density and high levels of urbanization. [1], [6]

Climate is a significant factor in the transmission dynamics in Sri Lanka. Aedes aegypti and Aedes albopictus mosquitoes are aided by rainfall to create breeding sites, and temperature and humidity help to drive mosquito development, longevity and viral replication rates. Rainfall studies have revealed lag effects such that incidence of dengue increases in the months following both the Southwest monsoon (2-8 weeks) and Northeast monsoon (2-8 weeks). [2], [5] The relationship is context dependent and non-linear, however, excessive rainfall can flush out breeding sites, or moderate rainfall, followed by warm temperatures can facilitate outbreaks.

The epidemiological patterns are further complicated by urbanization and human activities. Urban development and construction activities occur very quickly, solid waste management is inadequate, and water storage systems are poorly designed, leading to many artificial breeding containers. The spread of viruses is supported by high population densities and human mobility in micro-climatic zones particularly in and around Colombo. [2] District-level models do not necessarily reflect fine scale risk heterogeneity due to localized variability in microclimate, land use and socio-economic conditions.

A comparison of the incidence patterns in the dry-zone and the wet-zone regions of Sri Lanka suggests that climatic factors alone are not sufficient to explain incidence patterns. Human mobility and built-environment features seem to be more important in areas of high urban density and wetness, whereas weather features seem to be more important in drier and less-urbanized areas. The results highlight the importance of developing models that are based on more than just historical averages and one factor explanations and that include climate and context-based factors to overcome systematic prediction errors.

Patterns are also seen in adjacent countries like Malaysia and Indonesia, where long-term trends, seasonal components and spatial heterogeneity are dominant factors in the dengue dynamics. [9] Research employing seasonal-trend decomposition (STL) has revealed that the actual trend is sometimes as important as genuine seasonality, and there are considerable variations at the state or district level.

These are too complex and local to be addressed by traditional single-stage models. The residual compensation method chosen for this project is motivated by the fact that there are often exploitable information left in errors in baseline forecasts attributable to climatic anomalies, urbanization effects and unmodeled spatial factors. [1], [5], [6]

### 2.2.2 Data Sources and Feature Selection

The quality, granularity and relevance of the input features are important for effective dengue risk modelling. There are extensive studies that demonstrate the superior predictive power of the combination of epidemiological, meteorological/environmental and spatial/demographic data when compared to the power of any one of the data categories. This subsection summarizes the major categories of features that are applicable to the three modules in the proposed Residual Compensation Modeling Framework.

#### 2.2.2.1 Epidemiological Features

All three modeling modules base their historical dengue case data on the following. Studies are typically based on weekly or monthly numbers of confirmed or suspected cases from a national health surveillance system, such as a Ministry of Health registry. Weekly resolution is becoming more popular because of offering a compromise between resolution and noise reduction to enable early warning applications. [6], [9]

Important epidemiological characteristics are:

Raw and lagged case counts (usually 1-8 week lag)

Cumulative incidence

Trend and seasonal components obtained using decomposition, e.g. Seasonal-Trend decomposition using LOESS (STL).

Assign outbreak binary labels or risk categories based on historical thresholds

In Malaysia, studies have shown that STL decomposition is useful in extracting long-term trends from seasonal patterns and that the dynamics of the dengue were mostly affected by the trend. [6], [9] In Sri Lanka specific works, lagged case series and moving average have been very common as strong autoregressive predictor in SARIMA models and machine learning models. If the goal of the classification task is outbreak detection, the binary/ multi-class classification labels (e.g., low or medium risk/ high risk) are typically based on breaking thresholds on the number of cases.

#### 2.2.2.2 Meteorological and Environmental Features

Among the most important exogenous variables are climatic variables that directly influence Aedes mosquito breeding, their survival, and virus extrinsic incubation period. Typical features used are:

Rainfall (cumulative and lagged 2-8 weeks)

Average, minimum and maximum temperature.

Relative humidity

The differences between temperature and normal and humidity and normal.

The deviations of temperature and humidity from normal.

Rainfall-Temperatures interactions

In Rio de Janeiro, it was found that the use of lagged climatic variables in SARIMAX and LSTM models enhanced prediction accuracy over autoregressive models. In the same way, microclimatic data in finer scales have been used to improve the prediction of mosquito abundance and disease risk. Vegetation indices (NDVI), land surface temperature, and elevation are other common environmental variables that are also included because they influence local breeding site suitability.  [2], [5], [10] This phenomenon of non-linear and delayed response of these variables is what makes standalone statistical models often exhibit systematic residuals (SRE) that can be effectively captured by second-stage machine learning compensators.

#### 2.2.2.3 Spatial and Demographic Features

In fine-scale spatial modeling, it is essential to make explicit geographic and socio-demographic context. Some of the key attributes include:

Data on the location of cases (point or Grama Niladhari/MOH level)

This includes the population density as well as the age profile and urbanization rate.

Built-up areas, water bodies, vegetation (land use/land cover)

Elevation & topography

Mobility proxies (where available) and distance to high-risk zones.

Socioeconomic indicators (where data is available, but limited)

In recent years, spatial studies have been performed such as hotspot analyses (e.g. in West Java using Moran's I and Getis-Ord Gi*) and comprehensive risk mapping (e.g. in Shenzhen, integrating hazard, exposure, and vulnerability (in terms of socio-economic factors). Proximity to breeding sites and urban density are critical in Sri Lankan context since transmission is highly localized. [13], [14], [8]

The spatial and demographic characteristics are part of the third module (spatial hotspot detection) and are also needed to build the environmental correction terms in residual compensation models throughout the various modules.

### 2.2.3 Forecasting Approaches for Dengue Case Prediction

Accurate forecasting of dengue case counts is critical for proactive resource allocation and early warning. Studies in this area have progressed from the traditional statistical approaches to more recent, sophisticated machine learning techniques and more recently to hybrid approaches.

#### 2.2.3.1 Traditional Statistical Time-Series Models

Despite its limitations, the traditional statistical approach that has been widely used for dengue forecasting is Autoregressive Integrated Moving Average (ARIMA) and its seasonalized version, SARIMA/SARIMAX, having several advantages such as being interpretable, relatively simple to apply, and being able to model autocorrelation and seasonality.

In Sri Lanka, Karasinghe, et al., (2024) used a modified ARIMA model to predict the incidence of dengue cases on a weekly basis, finding it to be a good predictive model for Colombo district. Chathurangika et al. (2024) integrated seasonal weather patterns into forecasting systems with uncertainty quantification, emphasizing the importance of SARIMA-based systems for addressing the effects of monsoons.[5], [6]

Recently, Hamedin et al (2025) conducted a pan-Indonesia study in Malaysia using a combination of STL technique and ARIMA and SARIMA in weekly time series data (2022-2024). [9] They found many state-to-state differences, and long-term trends can be more apparent than seasonal changes. The STL algorithm was found to be suitable for the decomposition of trend, seasonal and irregular components, and the SARIMA model was needed for the states with the highest levels of seasonality. In many instances, the model was deemed adequate by residual diagnostics (Ljung-Box test, ACF plots), but the authors included noted limitations with the current non-linear climate effects and localized variations.

These models have two main advantages, the rigor of statistics used and the ease of interpretation. They tend to assume linear relationships, however, and have difficulty accounting for complex non-linear interactions between climatic variables and transmission dynamics, leaving systematic residuals associated with climatic anomalies, urbanisation effects and unmodelled factors.

#### 2.2.3.2 Machine Learning for Case Forecasting

Non-linear relationships and high-dimensional interactions are captured by machine learning models, which have become popular. The popular algorithms are Random Forest, XGBoost, Support Vector Machines (SVM), and the Long Short-Term Memory (LSTM) network.

In their extensive comparative study in Rio de Janeiro, Brazil, Chen and Moraga (2025) tested ARIMA, SARIMAX, Random Forest, XGBoost, SVM, LSTM, and Prophet (with and without climate covariates). They found that LSTM models outperformed the other models in most forecast horizons, especially when using the lagged temperature and humidity. XGBoost and Random Forest were also quite good, particularly for short-term predictions. The study highlighted the importance of the use of climate covariates and ensemble methods.[10]

On the other hand, ML models tend to perform better than pure statistical models in describing complex patterns; however, they may lack explicit temporal structure unless features are included in the model that are lagged or have recurrent structures. They are also typically less interpretable and can overfit in situations with limited data as are often encountered in public health surveillance.

#### 2.2.3.3 Hybrid and Residual Compensation Models

The hybrid and residual compensation models are also discussed.A discussion of hybrid and residual compensation models is also provided.

A hybrid approach with both statistical and machine learning aspects has been developed and has shown to be a promising alternative to make use of the benefits from both paradigms. One especially pertinent way to do this is with the residual compensation framework (or two-stage model) in which a baseline model makes initial predictions, and a second-stage model learns to predict and correct the residuals with other explanatory variables.

Francisco et al. (2024) suggested a hybrid machine learning method especially developed for zero-inflated dengue data. Their two-stage approach first conducts qualitative (presence/absence) prediction, and then quantitative prediction is conducted if cases are predicted. This blended type of approach greatly enhanced accuracy of fine-resolution spatiotemporal forecasting. [12]

However, the majority of the current dengue hybrid models are non-typical hybrid models, and have not been systematically formulated as residual compensation architectures. Very few studies explicitly design the second stage to correct and target the systematic errors left by a strong baseline (e.g., XGBoost/Random Forest second stage targetting the climate anomalies and contextual features corrected the SARIMA residuals). This is a major opportunity for the proposed framework, as the residual compensation is applied uniformly in all modules of forecasting, classification and spatial.

### 2.2.4 Outbreak Risk Classification Approaches

Unlike forecasting, which aims to forecast an exact number of cases, outbreak risk classification is dedicated to determining the risk of an imminent outbreak (binary and/or multi-class: outbreak/non-outbreak, low/medium/high risk). This probabilistic view is of special benefit to public health decision-making, which allows for precise risk level notification and resource allocation.

#### 2.2.4.1 Binary and Multi-Class Outbreak Classification

Machine learning classifiers have been extensively applied to dengue outbreak detection. Common algorithms include Random Forest, XGBoost, Support Vector Machine (SVM), and Artificial Neural Networks (ANN). [11] There is an ample amount of research using machine learning classifiers for dengue outbreak detection. Typical algorithms used are Random Forest, XGBoost, Support Vector Machine, and Artificial Neural Networks.

Exebio-Chepe et al. (2024) performed a comparative study on dengue virus (DENV) case classification based on the information of a public hospital in Peru (21,157 cases). They have tested SVM, Random Forest and ANN. The highest accuracy (86.47%) and good recall (92.91%) were obtained by the Artificial Neural Network and excellent sensitivity (99.05%) was obtained from SVM. This research demonstrates that clinical, demographic and temporal features of patients with dengue can be effectively distinguished using machine learning classifiers.

Delineation of weeks or regions as “outbreak” based on cases that are above a threshold that is based on historical averages or moving windows has been attempted using similar classification methods. The models are generally based on lagged case numbers, trend indicators and simple seasonal patterns.

#### 2.2.4.2 Environmental Anomaly Integration in Classification

The use of environmental variables brings a substantial improvement in classification. Rainfall anomalies, temperature anomalies from seasonal norms and humidity extremes provide features that capture environmental conditions favorable to the proliferation and virus transmission of mosquitoes.

Research indicates that models that include lagged meteorological anomalies (2-8 weeks) perform better than models based on raw case data or on absolute weather values. The approach of hybridization by Francisco et al., (2024) is pertinent here: They use a two-stage approach first, use machine learning to predict the occurrence of the disease qualitatively (binary), and then only use a quantitative estimation in the areas that are predicted to be positive. This approach is useful to address problems associated with zero-inflated data that are encountered when data is provided at finer spatial or temporal scales. Due to the influence of monsoons and the micro climatic variations in Sri Lanka, it is crucial to incorporate climate driven features in this context as the baseline classifiers are prone to misclassify the risk levels during the period of anomalous climatic conditions.

#### 2.2.4.3 Probability Correction and Ensemble Adjustment

There is an area of underexplored correction and calibration probabilities of classification. Typically, standalone classifiers can yield poorly calibrated probabilities of classification or systematic errors in their predictions when environmental conditions change. The classification module is designed to overcome this by training a second stage model to fine-tune the output probabilities of the baseline classifier using the environmental anomaly indicators and other contextual features.

Ensemble methods (twofold) (stacking, voting or boosting) and the probability calibration techniques (e.g., Platt scaling, isotonic regression) have been used in some infectious disease studies, while systematic residual-based correction frameworks specifically for dengue outbreak classification are limited. This is an important methodological opportunity for which the framework proposed in this document will address, as it will be the development of a dedicated residual compensation classifier that will refine baseline risk probabilities.

### 2.2.5 Spatial Hotspot Detection and Risk Mapping

Spatial analysis is essential for moving beyond aggregate predictions to identify precise geographic locations where interventions should be prioritized. This section is a review of the approach used to identify dengue hotspots and mapping the risk.

#### 2.2.5.1 Spatial Statistical Methods

Many spatial statistical methods are utilized for identifying clusters and hotspots in dengue incidence data. Global Moran's Index is often used to measure the overall spatial autocorrelation (random, dispersed, or clustered patterns), while Local Indicators of Spatial Association (LISA) and Getis-Ord Gi* statistics are used to detect the presence of high-high (hotspot) and low-low (coldspot) clusters in the neighborhood.

Mardhiyah et al. (2026) did spatial clustering and hotspot analysis of dengue fever in West Java Province, Indonesia during 2020-2024. They found that the distribution of the species was random in 2020 but became highly clustered in later years using Global Moran's Index. LISA analysis always showed high-high clusters in Bandung Regency, Bandung City, Bogor Regency, Bekasi City, and Depok City in urban and peri-urban areas. The Getis Ord Gi* also identified statistically significant hotspots. These results show the usefulness of the spatial autocorrelation techniques for detection of endemic pockets.[13]

These purely statistical approaches are very useful for identifying historical district level dengue surveillance patterns, but they do have one major drawback: there are no underlying environmental causes taken into account, and emerging risks could be missed in areas where climate or land-use change is taking place

#### 2.2.5.2 GIS and Remote Sensing Integration

The modern methods include the use of Geographic Information Systems (GIS), remote sensing and environmental data to create more detailed risk maps. This allows to integrate case information with climatic, topographic and socio-demographic layers.

To estimate the risk of being bitten by an Aedes mosquito, Lin et al. (2025) created a complex hazard-exposure-vulnerability model for Shenzhen, China. They modeled mosquito density (hazard layer) using the Optimal Parameters-based Geographical Detector (OPGD) and Geographically Weighted Random Forest (GWRF), and vulnerability by demographic and socioeconomic factors using the Geographically Weighted Principal Component Analysis (GWPCA). The built-in risk map was able to successfully identify high-risk subdistricts and highlight the drivers in every hotspot.[8], [14]

GIS-based environmental integration greatly enhances  the traditional case-only mapping approach by considering both environmental suitability for vector breeding and possible contact with humans. uch integration of rainfall, elevation, land-use, and population density data , land use data and population density would be very useful in Sri Lanka, where there is a wide range of terrain and extensive urbanisation.

#### 2.2.5.3 Spatial Residual Adjustment

Although several advances have been made with spatial modeling, the majority of studies use a single-stage model, either based on pure space statistics or based on a static environmental overlay. There are very few studies that use a residual compensation layer in the spatial risk estimation, which is done by applying baseline spatial hotspot surfaces generated using Kernel Density Estimation (KDE) and spatial autocorrelation analysis (Moran’s I) with a second stage model that takes into account environmental anomalies, demographic corrections, and other factors not modelled.

It is a sizeable contribution to the available literature. Baseline spatial models may leave systematic patterns associated with micro-climatic variation, interventions (such as fogging) and socio-economic gradients as residuals. In response, the proposed framework builds a spatial adjustment model, collects the residuals, and adjusts for them by incorporating contextual variables, such as rainfall, elevation, and temperature and population density, to improve hotspot detection accuracy and usability. The proposed framework further explores machine learning-based residual compensation approaches, such as Random Forest Regression, to improve hotspot prediction accuracy and spatial risk estimation.

### 2.2.6 Comparison of Approaches

Table 2.1 presents a comparative summary of the major methodological approaches reviewed in the preceding sections across the three core dimensions of dengue risk modeling. The comparison highlights the strengths and limitations of existing methods and underscores the need for an integrated residual compensation framework.

Table 1 : Comparison of Dengue Risk Modeling Approaches

It is evident from the table that none of the current methods meet all the requirements for a holistic, granular and actionable dengue risk prediction system. Interpretability is achieved in pure statistical models, but they are not flexible. Machine learning models are powerful in capturing complexity but fail to consider temporal/spatial structure and systematic error patterns. Spatial methods are effective at providing identification of This warrants the proposed Residual Compensation Modeling Framework that enhances the accuracy, robustness and practicality of the three dimensions by following a consistent two-stage correction approach.

### 2.2.7 Early Warning Systems and Visualization Dashboards

Effective visualization and decision-support interfaces are needed to make sophisticated predictive models useful for public health decision-makers. In recent years, several early warning systems and dashboards have been created for dengue, but little progress has been made in their integration and usability.

Yi et al. (2023) created a web-based application (PICTUREE-Aedes) for visualizing dengue data and predicting dengue cases.[3] The platform combines historical case information with environmental factors to produce visualisations and make short term predictions. It is innovative in integrating visualization with basic predictive features, but is mainly used to monitor national or regional aggregates and does not provide in a single consistent view, high spatial resolution and multi-dimensional risk outputs.

Likewise, Uelmen Jr. et al. (2023) developed a Global Mosquito Observations Dashboard (GMOD), a citizen science-driven user-friendly, web-based platform for invasive and vector mosquito monitoring.[4] The dashboard is a strength in terms of spatial visualisation of mosquito surveillance data, but it is not predictive. Does not include sophisticated time-series forecasting, outbreak risk classification or dynamic risk mapping by residual compensation.[3], [4]

At the national level, other systems in dengue-endemic nations, such as the Sri Lanka's current Ministry of Health dashboards, generally use static reports, retrospective maps and basic figures for numbers of cases. Most of these platforms exhibit a number of serious drawbacks:

Lack of real-time or near real-time interactivity - Most update infrequently and do not support dynamic filtering or scenario simulation.

Single-dimensional outputs - They rarely integrate quantitative forecasts, probabilistic risk levels, and spatial hotspots simultaneously.

Limited decision-support features - Few systems provide automated alerts, risk thresholds, or resource allocation recommendations.

Insufficient granularity - Many operate at district or provincial levels, limiting their usefulness for localized vector control interventions.

Absence of model transparency and uncertainty communication - Residual errors and prediction confidence are rarely visualized.

The deficiencies are obstacles to prompt and focused public health responses. The need for an integrated Command Center style dashboard, with outputs from residual-compensated forecasting, classification and spatial modelling, presented in an interactive and real-time interface is well understood. Such a system would allow health authorities to view the risks as they relate to several different dimensions, would provide automatic warning systems, and would provide more efficient deployment of resources.

The proposed solution directly addresses these gaps by implementing the three analytical modules to a central, interactive visualization platform using modern web technologies (React.js frontend, Leaflet.js/Mapbox for GIS, and Flask/Django for backend).

### 2.2.8 Evaluation Methods

Good evaluation is crucial in order to confirm model performance, compare models and show the improvements as a result of the residual compensation. A variety of measures are used in the literature, depending on the unique characteristics of the modeling problem.

#### 2.2.8.1 In the case of Time-Series Forecasting (Module 1)

These include commonly used quantitative metrics such as Root Mean Square Error (RMSE), Mean Absolute Error (MAE), Mean Absolute Percentage Error (MAPE), and Symmetric MAPE (sMAPE). [10], [9] These measures measure the accuracy of the forecasted number of cases. Other studies also highlight the need for a multi-step forecast horizon evaluation (1-4 weeks period, and the longer periods) e.g. Chen and Moraga 2025; Hamedin et al. 2025. The Diebold-Mariano test is widely suggested for statistically testing the superiority of hybrid or residual-compensated model over baselines and takes into account the autocorrelation of forecast errors.

#### 2.2.8.2 For Outbreak Risk Classification (Module 2)

Common measures of the classification performance are Receiver Operating Characteristic Area Under the Curve (ROC-AUC), Precision, Recall (Sensitivity), and Specificity. The reliability of predicted probabilities is evaluated using confusion matrix and calibration plot. Outbreak Prediction, because of the class imbalance (outbreaks are relatively rare events), is where the AUC of Precision-Recall is more important. For a comparison between SVM, Random Forest and ANN models, accuracy, recall and sensitivity were reported by Exebio-Chepe et al. (2024). [11]

#### 2.2.8.3 For the purpose of Spatial Hotspot Detection and Risk Mapping (Module 3)

The hotspot detection accuracy, spatial overlap (such as intersection over union with actual case locations), and corrected Moran's I or Getis-Ord Gi* statistics are used to evaluate spatial models. Mardhiyah et al., (2026) employed a combination of Global and Local Moran's I and LISA cluster analysis. Lin et al. (2025) used dengue case distributions for validation of their integrated risk maps, correlating the areas predicted to be high risk with the actual distribution of cases. There are also some emerging spatial cross-validation methods and area-under-the-curve (AUC) variants suitable for spatial data. [12],13]

#### 2.2.8.4 Overall Framework Evaluation

The complete Residual Compensation Modeling Framework will be based on a mixture of the above. Other holistic steps that can be taken include,

Comparative statistical tests such as Diebold-Mariano forecast test.

The percentage decrease in the residual variance is considered an indicator of improvement.

Utility metrics with respect to alerts' timeliness and false/true positive/negative rates in simulated operational scenarios

Other studies use a rolling window or expanding window validation to simulate the real world, where models are trained on the most recent incoming data.

## 2.3 Summary

The literature discussed in this chapter shows that there has been a lot of progress and critical needs in dengue risk modelling. Traditional statistical time-series models (SARIMA/SARIMAX) and decomposition techniques (STL) can offer interpretable baselines that can capture seasonality and autocorrelation, especially in the context of Sri Lanka and the region. Random Forest, XGBoost, LSTM, and SVM techniques are also machine learning methods that are effective in capturing non-linear relationships and have been successful in both forecasting and classification tasks. The identification of hotspots and risk zones has been improved by the use of spatial statistical methods (Moran's I, LISA, Getis-Ord Gi*) and integration of GIS/remote sensing. Moreover, a number of visualization platforms have been trying to make this transition between the model and the operational use.

However, there are some key strengths and constraints found in the literature. Most studies focus on a single dimension of the problem, namely prediction of case numbers or classification of outbreak risk, or mapping spatial hotspots, without considering the others. The independent models often result in systematic residuals that carry useful information about climatic anomalies, micro-environmental differences, urbanization effects, demographics etc. There are hybrid models that are emerging, but relatively few use a consistent residual compensation framing, which involves a strong baseline model, followed by a second stage learner to systematically correct the baseline model. In addition, there is a significant gap between academic modelling work and operational tools for decision support, with many dashboards being static, not being multi-dimensionally integrated, and limited to minimal interactivity and actionable alerts in real time. [12]

This literature review thus provides a solid foundation for the proposed Residual Compensation Modeling Framework. This project fills important gaps in the literature by implementing a uniform two-stage residual correction method for quantitative forecasting, outbreak risk classification, and spatial hotspot detection, and by integrating the three outputs above into an interactive Command Center dashboard. Chapter 3 provides a detailed methodology, architectural design and implementation of this framework.

# CHAPTER 3 – TECHNOLOGY ADAPTED

## 3.1 Introduction

The chapter highlights the technologies that have been chosen for the implementation of the "Residual Compensation Modeling Framework for Dengue Risk Prediction". It presents different aspects such as the programming languages used in the project, development tools, libraries, frameworks and services selected for the project's implementation. These technologies are helping to develop a hybrid two-stage (residual compensation) modeling approach that combines time-series forecasting, outbreak risk classification, spatial hotspot detection and a public health decision support dashboard for visualization.

## 3.2 Technology Adapted

### 3.2.1 Programming Languages

Python

The project uses Python as the primary language, as it is the most frequently used in data science, machine learning, and statistical modeling. Its large library of time-series analysis, spatial computing and web development tools make it well suited for the development of the residual compensation framework. Python allows easy integration of baseline models (e.g. SARIMA), machine learning compensators (e.g. Random Forest/XGBoost), spatial analysis and embedding in dashboards.

### 3.2.2 Development Environments/Tools

Several environments are utilized to support model development, experimentation, training, and deployment:

Jupyter Notebooks

Used to explore, preprocess, analyse, model and do basic experimentation with compensation models. It makes it easy to create a repeatable process to decompose time-series as well as to visualize the forecasts vs actuals.

Google Colab

Offers GPU/TPU resources in the cloud for more complex tasks like training ensemble models (Random Forest, XGBoost), hyperparameter tuning, and spatial analysis on bigger data sets. It is especially helpful for  testing residual compensation models and environmental feature integration.

Visual Studio Code (VS Code)

Serves as the main local IDE to create modular, production-ready scripts, data pipelines, API backends and dashboard components. It enables version control integration and debugging of the entire hybrid modeling workflow.

### 3.2.3 Libraries and Frameworks

Data Handling and Numerical Computing

Pandas & NumPy

Essential for data loading, cleaning, feature engineering (lagged variables, climate anomalies), and handling epidemiological and meteorological time-series data.

SciPy & Statsmodels

Used for statistical analysis, time-series modeling (SARIMA/SARIMAX), residual diagnostics, and decomposition techniques (e.g., STL).

Machine Learning and Residual Compensation

Scikit-learn

Provides tools for preprocessing, baseline classifiers, regression models, cross-validation, and evaluation metrics for the compensation stage.

XGBoost / LightGBM / Random Forest

Core algorithms for the residual compensation models. These learn patterns in prediction errors using lagged rainfall, temperature, humidity, and other contextual features to improve baseline forecasts and risk classifications.

imbalanced-learn

Handles any class imbalance in outbreak risk classification tasks.

Spatial Analysis

GeoPandas, Shapely, Fiona

For geospatial data manipulation and hotspot mapping.

PySAL / scikit-learn spatial tools / Matplotlib & Seaborn

Support spatial autocorrelation (Moran’s I), kernel density estimation, and hotspot detection with environmental corrections.

Visualization and Dashboard

Matplotlib & Seaborn

For exploratory data analysis, residual plots, and forecast visualizations.

Plotly / Dash or Streamlit

Interactive plotting and dashboard prototyping.

Leaflet.js / Folium

Web-based interactive GIS heatmaps for spatial risk visualization.

Web Development & Deployment

Flask / Django (Backend)

To serve ML models as APIs and power the command-center dashboard.

React.js (Frontend)

For building a responsive, interactive user interface with real-time alerts and scenario simulation.

### 3.2.4 Version Control and Collaboration

Git & GitHub

Git is used for version control, enabling team collaboration on different modules (forecasting, classification, spatial, dashboard). GitHub supports code review, issue tracking, and maintaining reproducible experiments across the residual compensation pipeline.

## 3.3 Summary

This chapter outlined the key technologies adapted for the Codexon project. Python serves as the core language, supported by powerful libraries for statistical modeling (Statsmodels), machine learning (Scikit-learn, XGBoost), spatial analysis (GeoPandas), and web visualization (Folium, Dash/Leaflet). Development occurs across Jupyter/Colab for experimentation and VS Code for production code, with GitHub ensuring collaborative development. These tools collectively enable the implementation of the two-stage residual compensation framework, integration of climate and contextual data, and delivery of an actionable early warning dashboard for dengue risk management.

# CHAPTER 4 – OUR APPROACH

## 4.1 Introduction

This chapter introduces the overall approach and methodology followed by the Team Codexon in creating the Residual Compensation Modeling Framework for Dengue Risk Prediction. The proposed solution is able to overcome some of the major weakness in the current dengue forecasting systems and adopts a hybrid two stages (residual compensation) modeling approach for three complementary analytical modules: time-series case forecasting, outbreak risk classification and spatial hotspot detection. They are all linked to a comprehensive early warning system, the interactive visualization dashboard, which helps with proactive public health decision making.

In each module, the framework is based on two phases in a sequence: (1) establishment of the base model that captures the common patterns and (2) compensation model that learns and corrects for systematic errors, from the environmental, climatic and contextual factors. This methodology improves the prediction accuracy by taking advantage of patterns in the model residuals that are not captured by individual models.

## 4.2 Proposed System

The Residual Compensation Modeling Framework comprises three mutually dependent modules that together offer a multidimensional perspective on dengue risk, magnitude (forecasting), probabilistic risk (classification) and geographic focus (spatial mapping). The system automatically collects the historical dengue incidence data, weather information (temperature, rainfall, relative humidity) and other contextual information to pass through the Hybrid models and provides actionable recommendations through a centralized command-center dashboard.

The architecture is modular and pipeline style, which enables independent development and optimization of each module and integrates the output of each at runtime, enabling real-time visualization and alerting of risks.

### 4.2.1 Module 1: Hybrid Time-Series Case Forecasting

This module focuses on predicting weekly dengue case counts at a fine spatial scale.

Input:

Historical weekly dengue case counts

Meteorological data (lagged rainfall, temperature, humidity)

Temporal features (trend, seasonality, lagged cases)

Process:

Stage 1 (Baseline Model): A SARIMA/SARIMAX model is employed using historical weekly dengue cases to capture trend, seasonality, and autocorrelation structures inherent in the time series. [6]

Stage 2 (Residual Compensation): The residuals (Actual cases – Baseline prediction) are modeled using a machine learning regressor (Random Forest or XGBoost). This compensation model learns patterns in prediction errors using lagged climatic variables (rainfall 2–6 weeks prior, temperature, humidity), seasonal anomalies, and other contextual features.

Output:

The compensated prediction is obtained by adding the baseline forecast and the predicted residual, resulting in improved accuracy over standalone time-series models.

Users:

District-level health authorities and decision-makers for early warning and alert triggering.

### 4.2.2 Module 2: Hybrid Outbreak Risk Classification

This module classifies the likelihood of an impending outbreak (low/medium/high risk) rather than exact case counts.

Input:

Historical weekly dengue case counts

Environmental and climatic data (rainfall, temperature, elevation)

Population density and demographic layers

Process:

Stage 1 (Baseline Model): A baseline classifier (Random Forest or XGBoost) uses lagged case counts, trend features, and basic epidemiological indicators to generate initial outbreak probabilities.

Stage 2 (Residual Compensation): A second-stage model adjusts these probabilities by learning residual errors using environmental anomaly indicators, climate variability, and demographic factors.

Output:

Probabilistic risk levels that trigger intuitive alerts, aligned with established dengue risk clustering frameworks.

Users:

District-level health authorities and decision-makers for early warning and alert triggering.

### 4.2.3 Module 3: Hybrid Spatial Hotspot Detection

This module is designed to detect, describe and identify geographic areas at high risk of dengue.

Input:

Geocoded historical dengue case locations

Environmental and climatic raster data (rainfall, temperature, elevation)

Population density and demographic layers.

Process:

Stage 1 (Baseline Model): In stage 1 (Baseline Model) the locations of historical cases are used in conjunction with Kernel Density Estimation (KDE) and spatial autocorrelation measures (such as Moran's I) are used to produce preliminary risk surfaces.

Stage 2 (Residual Compensation): Residuals are compensated for using a spatial adjustment model including environmental corrections (rainfall, temperature, elevation, population density) through the application of Geographically Weighted models or ensembles of trees.

Output:

Dynamic Hotspot maps which present high-risk areas not identified by temporal models only. [7]

Users:

Vector control teams and field officers for targeted interventions and resource allocation.

## 4.3 System Integration and Early Warning Dashboard

All three modules generate outputs that are brought together in a central early warning system. The system provides automated visual alerts when predicted cases are greater than the predetermined thresholds or if the outbreak risk is "elevated". The interactive dashboard allows public health officials to:

Display forecasts for time series with intervals of uncertainty

Discover spatial heatmaps, and use drill-down functionality.

Simulate intervention scenarios

It is the intention of the dashboard to close this modeling-to-decision-making gap [3].

The implementation and data flow is as follows:

Historical data of dengue from official source and meteorological data from APIs are preprocessed such as cleaning, feature engineering with lags and normalization. The first stage is a stage of processing data independently by each module and the compensation stage is a stage of processing data together. The standard metrics used for model training, validation (time-series cross validation), and evaluation are MAE, RMSE, accuracy, and AUC. Final integrated pipeline can be used for batch processing for historical analysis and for near real time forecasting.

Figure 1: End-to-End Process of the System

## 4.4 Summary

In this chapter, the hybrid residual compensation approach, which Team Codexon adopted, was detailed. The framework systematically corrects the baseline model errors, across all forecasting, classification and spatial modules, with climate and contextual signals, thereby providing more accurate, granular, and actionable dengue risk intelligence. The system integrated with the models outputs the results in a simplified dashboard format, enabling health authorities to shift from reactive outbreak response to proactive prevention.

# CHAPTER 5 – ANALYSIS AND DESIGN

## 5.1 Introduction

In this chapter, the analysis and design of the proposed research, namely "Hybrid residual compensation modeling framework for dengue risk prediction", is presented. The goal of this system is to make the dengue prediction more accurate and reliable by combining the two stage learning process with traditional statistical modeling and machine learning technique.

Traditional dengue forecasting approaches tend to use one-stage models, which may be inadequate in capturing the nonlinearity and the external factors like climate. To overcome these drawbacks, the proposed approach applies the sequential modeling scheme: A base model is first constructed to discover the main trends in the data; A second model is designed based on the error between the base model and the original data, to improve the accuracy of the final model. The latter strategy allows the system to minimize the systematic prediction errors and generate stronger outputs.

## 5.2 Overall system architecture at a high level

The high-level architecture of the proposed dengue risk prediction system is presented, outlining the structure and data flow within the system. The design is systematic and pipeline-based, with several data sources combined, systematic preprocessing of data and using hybrid modeling methods to achieve accurate and interpretable results.

The overall system has been designed as an integrated early warning and analytical system, bringing together epidemiological, meteorological and spatial data, to get a complete picture of the risk of dengue. The architecture can be divided into five key sections: Data Acquisition, Preprocessing and Feature Engineering, Hybrid Modeling, Evaluation, and Output Visualization. These layers are applied in order, taking raw data from users to generate meaningful information to aid decision-making and early intervention.

In the first stage, the data acquisition layer is used to obtain datasets of different types that need to be analyzed. The data used for modeling temporal trends includes historical epidemiological data, including weekly dengue case counts. Furthermore, climatic data like rainfall, temperature and humidity are added, to represent environmental conditions that can affect the transmission of dengue. Where available, spatial and contextual data (geographic case location, population density, environmental indicators) are also incorporated to increase the capacity of the system to model spatial variability and localized risk.

After the raw data has been gathered it enters the Preprocessing and Feature Engineering layer where it is cleaned, transformed, and standardised for modelling. This includes addressing missing data, inconsistencies, and standardizing all data to a consistent temporal scale, usually weekly. At this point, feature engineering is a major focus, generating new features that contribute to model performance. These include statistics that reflect delayed effects of rainfall and temperature, seasonality (cyclical patterns) and trend indicators (e.g. moving averages). The system creates these informative features, thus improving the ability to learn linear and nonlinear relationships of data.

This processed data is then introduced to the hybrid modeling layer which represents the main component of the proposed system. This layer is composed of three analytical modules that run concurrently – time-series forecasting module, outbreak risk classification module and spatial risk mapping module. These modules are all based on the same two-stage residual compensation structure: a base model is used to extract the basic structure of the data, and a second stage model is trained from the error residuals of the base model. The results generated at both stages are merged to get the final prediction which helps to eliminate the systematic prediction errors and boost the accuracy. The overall design increases the accuracy of the prediction as well as consistency across various types of analyses in the system.

After the modelling process, the outcome is checked in the evaluation and model selection layer and performance of the baseline model and hybrid model is measured with the help of suitable metrics. This can be any of the error based metrics of forecasting, any of the classification performance measures, or spatial validation measures, depending upon the module. The main objective with this layer is to assess the success of the residual compensation approach and to show its superiority over the traditional single-stage models.

Lastly, the outputs are conveyed in the visualization and output layer, which converts the raw model predictions into more interpretable and useful insights for action. This comprises time-series plots of forecasts, probability-based dengue outbreak classification indicators and spatial heat maps identifying hotspot areas. The outputs can be used to build a dashboard or report interface that allows stakeholders to easily digest the results and inform decisions on resource allocation and interventions.

The system architecture is designed to be flexible and adaptable, allowing it to evolve as new methods and tools are developed and incorporated. The system architecture is designed to be flexible and adaptable, enabling it to evolve as new methods and tools are developed and introduced. The proposed system not only integrates temporal forecasting, risk classification, and spatial mapping into a single hybrid modeling method to overcome the drawbacks of independent predictive models, but it also offers a more comprehensive solution for dengue risk prediction and early warning.

Figure 2 : Top Level Architecture of the Proposed System

## 5.3 High-Level Architecture of Individual Modules

### 5.3.1 Module 1: Hybrid Time-Series Case Forecasting

Figure 3: Module 1: Hybrid Time-Series Case Forecasting

### 5.3.2 Module 2: Hybrid Outbreak Risk Classification

Figure 4 : Module 2: Hybrid Outbreak Risk Classification

### 5.3.3 Module 3: Hybrid Spatial Risk Mapping & Hotspot Detection

Figure 5 : Module 3: Hybrid Spatial Risk Mapping & Hotspot Detection

## 5.4 Summary

This chapter discussed the analysis and design of the proposed dengue risk prediction system that is designed as a hybrid residual compensation system. The system design brings together epidemiological, meteorological and spatial data into a well-defined pipeline that results in accurate and meaningful predictions.

One of the important parts of the design is a two-stage modeling process that is applied to three modules: time-series forecasting; outbreak risk classification; and spatial risk mapping. Each module consists of a baseline model which represents the basic features of the data, followed by a residual compensation model that reduces prediction errors.

In summary, the proposed design offers a comprehensive and flexible approach that integrates temporal, probabilistic, and spatial analysis, which will help improve the potential for reliable forecasts and facilitate effective early warning and decision-making.

# CHAPTER 6 – IMPLEMENTATION

## 6.1 Introduction

This chapter outlines the implementation of the Residual Compensation Modeling Framework (RCMF) for the prediction of dengue risk, including the datasets that were included and the pre-processing that was performed on the three analytical modules. Data from three main sources were collected: (1) weekly district-level dengue case count data from the Weekly Epidemiological Reports published by the Epidemiology Unit of the Ministry of Health Sri Lanka (2) meteorological reanalysis data from the NASA POWER API, provided for each district centroid in Sri Lanka, and (3) spatial environmental data such as CHIRPS rainfall rasters, WorldPop population density grids, and GADM district boundary shapefiles. After data collection, module-specific preprocessing pipelines were run to perform the following steps: temporal alignment, missing value treatment, lag feature engineering, outbreak label construction, raster alignment, and appropriate train-test splitting strategies, as detailed in the sections that follow.

## 6.2 Datasets Incorporated

Implementation of the Residual Compensation Modeling Framework is based on data sets from various sources that include epidemiological surveillance, meteorological reanalysis and geospatial repositories. The datasets were chosen because they were relevant to one or more of the three analytical modules. Each dataset is described in detail in the following sub-sections where the source, structure, coverage and role of the dataset in the framework are presented.

### 6.2.1 Epidemiological Dataset : Weekly Dengue Case Counts

Dengue case count data has been gathered for each week from the Weekly Epidemiological Reports (WER) published by the Epidemiology Unit, Ministry of Health Sri Lanka on the following link: epid.gov.lk. The data set contains the weekly dengue surveillance data for the 25 administrative districts of Sri Lanka. This dataset collected from the records includes the following information for each record: Epidemiological year, epidemiological week number, start date of the week, end date of the week, district name, and the number of dengue cases reported in the district and week. The data period was from 2007 to 2025, reflecting a number of outbreak cycles similar to those in previous studies on dengue forecasting in Sri Lanka.

The dataset shows the well documented bimodal seasonal dengue transmission pattern in Sri Lanka, the two peaks occurred in the southwest monsoon (June to July) and northeast monsoon (October to December). This seasonal structure is a key feature of the Sri Lankan epidemiological context, and directly influences the SARIMA seasonal order configuration in Module 1 and the monsoon indicator features engineered in Modules 1 and 2. The case burden is consistently high in Colombo, Gampaha, Kalutara and Kandy districts, with the Western Province and its neighbouring high population density urban centres being the most impacted by dengue transmission.

This data set is used in two different ways in the framework. For Module 1, weekly case counts from the districts are the only inputs into the Stage 1 SARIMA base model and lagged case features in the Stage 2 compensation model. In Module 2, the same set of cases are converted into binary and multi-class outbreak labels using an adaptive threshold procedure, which provides the target variable for both parts of the classification pipeline. In Module 3, aggregated case counts per district are used as spatial weights in the kernel density surface estimation.

### 6.2.2 Meteorological Dataset : NASA POWER

Meteorological data was obtained using the NASA POWER (Prediction Of Worldwide Energy Resources) API service provided by NASA's Global Modeling and Assimilation Office. MEDIAN is based on the MERRA-2 (Modern-Era Retrospective Analysis for Research and Applications, Version 2) reanalysis model, which offers gap-free and continuous meteorological data from 1981 to the present with a 0.5° X 0.625° spatial resolution. MERRA-2 is a physically-consistent global atmospheric model, which incorporates satellite observations and ground-based measurements in a coherent way to provide a reliable source of historical climate variables, where dense ground station networks are not available.

Centroid coordinates of each of Sri Lanka's 25 administrative districts were used for API queries and the temporal range was selected to match the period of the epidemiological study. Each district centroid daily record was returned and then aggregated to weekly timestep in order to match the weekly timestep of the expanded epidemiological cases count data. The daily precipitation data were added up to give weekly totals and average the temperature and humidity data for each weekly period. Below are the list of meteorological parameters retrieved.

Table 2: NASA POWER Meteorological Parameters Retrieved

This data is the major source of climate features for Modules 1 and 2, and is the data from which lag features and anomaly features are generated. The weekly precipitation sum is the most important climate influence in the residual compensation models, and in line with the 4-10 week lagged relationship between precipitation events and subsequent dengue case increases in Sri Lanka. The district-level PRECTOTCORR values are supplemented with the spatially continuous CHIRPS rainfall raster described in Section 6.2.3 for grid-level spatial analysis for Module 3.

### 6.2.3 Spatial and Environmental Datasets : Module 3

To perform spatial baseline modeling and environmental compensation in Module 3, a multi-source raster and vector data stack will be needed. Four different geospatial datasets were downloaded from open geospatial repositories, each providing a different aspect of environmental or demographic risk data.

District Boundary Shapefile: Sri Lanka's administrative district boundary polygons were downloaded from the GADM (Global Administrative Areas) database at administrative level 2 (ad2) from gadm.org. The shapefile contains geometry of all 25 WGS84 (EPSG:4326) districts as polygons. The geometry of these polygons was used to generate district centroid coordinates that were used as representative points for kernel density estimation (KDE) of the number of reported cases. When individual-level case location coordinates are not publicly released, this is referred to as areal smoothing of aggregated data, and is a commonly used proxy method in spatial epidemiology.

Rainfall Raster - CHIRPS: The weekly rainfall raster data was obtained from CHIRPS (Climate Hazards Group InfraRed Precipitation with Station data) from the University of California Santa Barbara Climate Hazards Center. CHIRPS is a combination of satellite-derived estimates of infrared cold cloud duration with ground station observations to generate gridded precipitation surfaces, 0.05 degree (~5 kilometres) resolution. Daily CHIRPS GeoTIFF were downloaded for the study period and summed up to the weekly scale. CHIRPS offers spatially continuous estimates of rainfall surfaces which have more information about sub-district precipitation variability than are captured by the point-based rainfall estimates provided by NASA POWER district centroid estimates, thus, CHIRPS is the most preferred rainfall input for the spatial compensation model.

Population Density - WorldPop: Data on population density was derived from WorldPop Sri Lanka, a 100 metre resolution gridded population density data released by the WorldPop team with constrained top-down estimates for 2020 from worldpop.org. Population density is an important dimension of human exposure to disease and under comparable environmental conditions, high-density areas will have a higher probability of disease transmission than lower-density areas, and population density will be an important covariate to discriminate between areas that are favorably set up for disease vs. areas that will be favorably located for outbreaks.

### 6.2.4 Dataset Summary

Table 2 provides a consolidated overview of all datasets incorporated across the three modules.

Table 3: Summary of Datasets Incorporated

## 6.3 Implementation of Modules

The pre-processing steps of each of the three analytical modules are described. A different form of preprocessing was necessary for each module, depending on the type of input data and two-stage residual compensation design of the module. The modules 1 and 2 are based on tabular time-series data, and share a common ground epidemiological-meteorological dataset, which is then further processed with feature engineering specific to the module. Module 3 is based on a spatiotemporal raster-vector data stack and needed to be loaded into a temporal and spatial (spatial preprocessing) pipeline, which is separated from the rest of the pipeline. Each module has its own set of preprocessing steps that are detailed in the sub-sections below.

### 6.3.1 Module 1 - Time-Series Forecasting Preprocessing

#### Data Merging and Temporal Alignment

Data from the weekly dengue case count and NASA POWER meteorological records were joined together into a master dataset using a composite key (district name and epidemiological week). A week-mapping function was used to map the Ministry of Health's epidemiological week numbering system to calendar-aligned ISO week dates before they were merged to ensure temporal correspondence between the two data sources. The merged dataset has one row for every district per week, and each row includes the reported count of dengue cases, the weekly mean temperature (T2M), the weekly mean of daily maximum temperature (T2M_MAX), the weekly mean of daily minimum temperature (T2M_MIN), the weekly mean relative humidity (RH2M), and the weekly precipitation sum (PRECTOTCORR). The pre-filtered and pre-excluded data at the district-week level is about 23,000 records in total across 25 districts.

#### Missing Value Treatment

A systematic review of the combined data set was carried out to identify and fill missing data. Epidemiological case count gaps are due to known reporting delays in publication of the Weekly Epidemiological Report and were handled by treating the gap as a percentage of the reported length of the gap. One to two consecutive missing weeks in a district's time series were filled in by linearly interpolating between the points between the missing weeks to maintain the local trend without causing distortion. Single week gaps, that were present in isolation, were filled with forward fill from the previous week's observed value. The NASA POWER meteorological columns did not require imputation since by construction the MERRA-2 reanalysis model generates a physically complete atmospheric simulation with no missing values.

#### Lag Feature Engineering

The merged master dataset was used to create lag features to input into the Stage 2 residual compensation model. Lagged dengue case count columns have been created at 1, 2, 3, and 4 weeks to help capture the short-term autocorrelation structure of the case series in the base model SARIMA that may not be fully captured in the residuals. Lagged WPSs were calculated at 2, 4, 6 and 8 weeks. This range covers the epidemiologically-supported period of 4 to 10 weeks between large rainfall events and subsequent increases in dengue cases in Sri Lanka, which is the cumulative time needed for the mosquito life cycle, viral incubation, and reporting delay. The lagged weekly mean temperature and relative humidity columns were calculated at 1, 2, 3 and 4 weeks. Further, to account for short-term dynamics that can be systemically underrepresented in the SARIMA baseline, a 4-week rolling mean of dengue cases was calculated and incorporated into the SARIMA model as a column, along with a column of the percentage change from week to week.

#### Anomaly Feature Derivation

Each district-week observation was used to calculate temperature, humidity and precipitation anomaly features. The long term mean value for each variable was defined as the mean value of the variable over the corresponding epidemiological week number in all training years and for each district. The weekly value measured in the given district was then considered to be “anomaly” when compared to this “long-term district-week mean”. These anomaly columns are meant to reflect the differences in the weekly climate from the normal weekly conditions, e.g., a wetter-than-normal week in the dry season or a hotter-than-normal week during inter-monsoon, and are expected to provide a better signal for the compensation model than the raw meteorological values, which already have a good signal via the seasonality shared with the case count series.

#### Seasonal Indicator Encoding

Seasonal indicator features were designed to explicitly indicate to the compensation model the location of each observation in the annual cycle. The two cyclical features (sin(week number) and cos(week number) each scaled to a 52-week cycle) were used to encode the epidemiological week number in order to retain the circularity of the weekly signal and prevent an artificial discontinuity at the end of week 52 and the beginning of week 1. The following two binary dummy monsoon season variables were included: Southwest monsoon (1 for epidemiological weeks 20 to 38, May to September) and Northeast monsoon (1 for epidemiological weeks 44 to 52 or 1 to 8, November to February). These dummies can help the compensation model to view the two high-risk seasons as two separate seasons as opposed to inter-monsoon seasons.

#### Train/Test Split

Preprocessed dataset was split into training and test subset using temporal holdout split. The 2007 to 2023 observations were used for the training set, while the 2024 to 2025 observations were used as the held-out test set. The choice of deliberately avoiding a random split was made with the intention of avoiding a form of data leakage that would occur if a time-series data set was randomly split into a training set and a test set, where observations in the future would be in the training set and observations in the past would be in the test set, negating the temporal validity of the forecasts' evaluation.

### 6.3.2 Module 2 - Outbreak Risk Classification Preprocessing

#### Outbreak Label Construction

The binary outbreak label was generated by using weekly dengue cases data from the district using an adaptive thresholding procedure. A district-week observation was labeled as an outbreak when the number of reported cases in that week for that district was above a threshold value calculated as the mean plus 1.5 standard deviations of reported cases for that district in that week for all training years. This threshold was calculated separately for every district and week (25 × 52 thresholds in total). This threshold is designed to be adaptive, district specific, and week specific for a number of reasons. It takes into account the significant difference in the baseline counts of dengue cases in different districts of Sri Lanka, with a routine week of cases in Colombo representing a true outbreak in a low-burden district, like Mullaitivu. Second, it recognizes the seasonal pattern of dengue transmission and does not mistakenly label the high number of cases during the peak season as an outbreak if they are in line with the historical pattern of transmission for that district and week combination.

In parallel, a multi-class label was obtained with the same district-week historical distributions. The observations that were below the district-week mean were placed in the Low risk class, between the district-week mean and one standard deviation above the mean were classified as Medium risk class, and one or more standard deviations above the district-week mean were classified as High risk class. The binary and multi-class label formulations were both kept to compare the performance of the classification models.

#### Class Balance Assessment

The class distribution of outbreaks versus no outbreaks weeks was analyzed for the entire training set. As predicted, the outbreak class was the smaller proportion of all district-week observations in the training data, as genuine outbreaks of dengue are rare and sporadic compared to endemic background transmission. To correct this, weights were applied in the base classifier's training configuration inversely proportional to the frequency of each class, making it more costly to misclassify the outbreak class (which was the minority class) than to misclassify the non-outbreak class (which was the majority class). In addition, the SMOTE (Synthetic Minority Over-sampling Technique) oversampling method was tested as an alternative imbalance correction method but was only used on the training fold during the cross-validation process and not used for evaluation to preserve the class proportions of the real-world test set.

#### Stage 1 Feature Construction

The base classifiers were Stage 1 features prepared without the environmental data, to ensure the data was suitable for the base classifiers. The idea behind such a separation is fundamental to the residual compensation architecture, in which the base classifier aims to capture the predictable temporal structure of outbreak risk; systematic errors due to environmental anomalies are removed by the Stage 2 compensation model. The Stage 1 feature set included lagged dengue case counts at 1, 2, 3 and 4 weeks; a 4-week rolling mean of dengue case counts; the rate of change in dengue case counts in the week before; binary variables for the southwest and northeast monsoon season; and the sine and cosine encoding of the epidemiological week number, as described in Section 6.3.1.

#### Stage 2 Feature Construction

The Stage 2 compensation model was expanded with the feature set of the environmental anomaly signals that were missing from Stage 1. The columns derived in Section 6.3.1 (rainfall anomaly, temperature anomaly, and humidity anomaly) were included, as well as lagged residuals from the base model (the difference between the actual outbreak label and the base predicted probability for each of the last two weeks). The base outbreak probability output from Stage 1 was passed directly as an input feature to the compensation model to enable explicit correction of the base estimate, in addition to the same monsoon dummy variables and encoding of weeks of the year used in Stage 1. The lagged residual features give the compensation model a short-term memory of the recent systematic error in the base classifiers outputs giving it the ability to correct for systematic errors that are present in the base probability estimates over a long period of time.

#### Train/Test Split

The same temporal holdout split applied in Module 1 was used for Module 2, with training data spanning 2007 through 2023 and test data spanning 2024 through 2025.

### 6.3.3 Module 3 - Spatial Hotspot Detection Preprocessing

#### Vector Data Preparation

The district boundary polygons of Sri Lanka (GADM Level 2) were loaded from the shapefile into a GeoPandas GeoDataFrame and found to be in geographic coordinate system (EPSG:4326). A set of 25 point locations, one for each district, was created using the centroid method from GeoPandas on each polygon geometry. This GeoDataFrame was merged with weekly dengue case counts from the epidemiological dataset described in Section 6.2.1 using the district name as the "merge key," to create a spatiotemporal vector data set with one record per district per week with its corresponding centroid geometry, weekly number of cases and cumulative number of cases over all the time period for use as a spatial weight.

#### Raster Ingestion and Alignment

The weekly rainfall GeoTIFFs were loaded with the rasterio library in python, as well as the SRTM elevation GeoTIFF and the WorldPop population density GeoTIFF. Before processing, each raster layer was examined to ensure the layer has its own native coordinate reference system and spatial resolution. The elevation layer SRTM was acquired in WGS84 at 30 metre resolution and did not need to be reprojected. CHIRPS rainfall layers were confirmed to be compatible in space, and are available at a native spatial resolution of 0.05 degree in WGS84. The WorldPop population density layer was resampled from 100m to 0.05 degree resolution to accommodate the CHIRPS grid. To resample a continuous raster layer (Rainfall), bilinear interpolation was used to maintain smooth spatial gradients. A population density layer was resampled to prevent any non-integer artefacts in the count-based density values with nearest-neighbour interpolation. Before going to feature extraction, all layers were found to have a common spatial extent (Sri Lanka's geographic extent) and a common grid definition.

#### Baseline Spatial Risk Surface Generation

The spatial domain of Sri Lanka was divided into a weighted kernel density surface using 25 district centroids as the point locations and the spatial weight of each centroid was assigned as the cumulative number of reported dengue cases in the respective district during the study period. A Gaussian kernel function was used, and the bandwidth parameter was set following the Silverman rule of thumb, based on the spatial distribution of weighted centroid coordinates. This procedure generates a continuous risk surface that quantifies the country-wide spatial intensity of dengue burden while smoothing the surface based on the dengue burden of each district by geographic proximity. A series of sensitivity tests were performed over a set of bandwidth values to determine the stability of the resulting surface and if there was a material sensitivity to the kernel bandwidth.

The Moran's I statistic of spatial autocorrelation was calculated for district-level aggregated KDE values based on a queen contiguity spatial weights matrix, where a district is viewed as being a neighbour to every other district that shares a corner or boundary. The positive value of Moran's I index indicates that the baseline risk surface represents true geographic clustering of the dengue burden and not spatial randomness. The Moran's I result and corresponding permutation-based p value were documented as a formal validation of the spatial baseline in Stage 1.

#### Raster-to-Tabular Conversion

Point sampling (using the rasterio sample method) was used to extract raster values from all the layers aligned on the spatial domain, sampled at the 25 district centroids. The extracted values were the weekly rainfall sum for each week of the study time period, the SRTM elevation value (static covariate), and the WorldPop population density value (static covariate) for each district centroid. In this extraction step, the extracted values were then added to the spatiotemporal vector dataset created in the vector data preparation step to create a flat tabular dataset, with each row representing a district-week combination and each column containing the number of dengue cases observed, the KDE baseline risk estimate for the district, as well as the average weekly precipitation, elevation, and population.

The residual is the difference between the district-week case intensity observed and the KDE baseline (expected) district-week risk estimate, and was the variable used in the Stage 2 spatial compensation model for the target. A positive residual means that the district had more cases than the spatial baseline would suggest based on its geographic location and total burden, therefore, environmental and/or demographic variables were associated with an increase in case intensity during that time period. Negative residues suggest that the intensity is less than predicted at baseline, reflecting suppressive environmental factors and/or the impact of intervention activities.

#### Spatial Cross-Validation Preparation

In order to avoid spatial leakage in the evaluation of the Stage 2 compensation model, a spatial cross validation approach was used for evaluation instead of commonly used random k-fold cross validation. Sri Lankan 25 districts were divided into five spatial folds via geographic clustering method, which is based on proximity of centroids. The centroids of districts were clustered using the KMeans clustering algorithm. This guarantees that the environmental conditions, mosquito dynamics, and epidemiological features of geographically adjacent districts are highly correlated and therefore would not end up in both parts of the training set and test set at the same time. Spatially held-out folds can be used to better assess the generalization performance of the compensation model to geographies outside of the fold than random fold assignment can offer.

## 6.4 Summary

The chapter outlined the datasets that were included and preprocessing pipelines performed in the three analytical components of the Residual Compensation Modeling Framework. All multi-source data essential to the framework were collected, and weekly dengue case counts were obtained from the Epidemiology Unit of the Ministry of Health Sri Lanka, meteorological variables from NASA POWER, and spatial environmental variables from CHIRPS, SRTM and WorldPop. In Module 1, preprocessing focused on temporal alignment, lag feature engineering for case counts and climate variables, anomaly feature derivation and a temporal train-test split; in Module 2, an adaptive approach for constructing district-week outbreak labels was applied, and a two-stage feature separation was explicitly designed to preserve the residual compensation architecture; and in Module 3, weighted centroid based KDE surface generation, multi-source raster alignment, raster-to-tabular feature extraction and spatial cross validation were performed, to construct a fold split. The next step is to implement an all three module training model in Stage 1 followed by residual extraction and Stage 2 compensation model building; the full hybrid pipelines are then tested against the held out test sets.

# CHAPTER 7 – DISCUSSION

## 7.1 Introduction

This chapter reviews the latest developments in our Residual Compensation Modeling Framework for Dengue Risk Prediction research. It showcases the progress made to date, challenges faced and future work to fully develop an integrated early warning system for dengue risk management in Sri Lanka.

## 7.2 Current Progress

The project started with a thorough literature review to understand the state of the art in dengue forecasting, spatial analysis, and machine learning application to vector-borne disease prediction. The project began by reviewing the existing literature on dengue forecasting, spatial analysis, and machine learning applications for vector-borne disease prediction. We reviewed several research works on time-series modeling, patterns of residuals in predictions and spatial hotspot identification to provide a good theoretical background for our hybrid approach [8].

Good progress has been achieved in acquiring and pre-processing data. Historical data of dengue incidence in weekly time scale has been compiled and correlated with meteorological parameters (Temperature, Rainfall, Humidity). Cleaning and filling missing values of the main datasets have been performed, and feature engineering and exploratory data analysis have been performed (lagged variables). Initial time-series decomposition using STL and baseline SARIMA/SARIMAX models have been implemented and tested, providing a solid foundation for the forecasting module. [6].

We are starting the development of the second stage machine learning models (Random Forest and XGBoost) that will learn from the residuals of the baseline model for the residual compensation component. Initial experiments indicate that there are potential benefits in forecast accuracy when lagged climatic features are included. Furthermore, spatial analysis, in particular Kernel Density Estimation and Moran's I, has been started to detect the dengue hotspots and will be added during the compensation phase with the environmental corrections. [8].

A module to classify the risk of an outbreak is also being developed, and baseline classifiers are being benchmarked based on historical trends of the case and environmental data. The architecture of the overall system is designed and initial prototyping of the Web-based dashboard has begun with the modern visualization tools.

## 7.3 Challenges Encountered

In the first stages there were problems of data availability and data quality. Dengue case data is not available at sub-district level, and is sparse and coarsely aggregated. The temporal linkage of dengue records and meteorology was also challenging because of the different reporting frequencies and sources of the two datasets. Moreover, the incidence of dengue is zero-inflated at finer scales making quantitative modelling challenging, and this is being tackled with hybrid qualitative–quantitative modelling approaches. [12]

## 7.4 Future Work

During the next steps, the residual compensation models in all three modules will be implemented and optimized in their entirety. This involves thorough hyperparameter optimization, time-series cross validation, and a detailed performance analysis with metrics like MAE, RMSE, accuracy, and AUC.

All three hybrid modules will be combined into a single pipeline and the integrated interactive command-center dashboard will be developed. This dashboard will include real-time forecasts and alerts for the risk level, dynamic hotspot maps, and scenario simulation to assist public health decision making [3].

Additional work will focus on model interpretability (via SHAP values), uncertainty quantification and validation with recent outbreaks of dengue. Other variables such as population density, intervention data (fogging records) and urbanization variables are also planned to be added to improve the robustness of the model.

The final stage of the project will involve deploying the system in a test environment, conducting user acceptance testing with relevant stakeholders, and preparing the framework for potential real-world integration with national health surveillance systems.

## 7.5 Summary

The Residual Compensation Modeling Framework holds significant promise to address some of the challenges of existing dengue forecasting systems, as it explicitly takes into account climate and contextual variables in a systematic way to correct for model residuals. The outcomes from the work done for data preparation, baseline modelling and first experiments with compensation, offer good foundation to deliver an accurate, granular and actionable early warning system. Further development in the coming months will be dedicated towards full integration, optimization, and deployment to facilitate proactive dengue prevention and control, in Sri Lanka.

# REFERENCES

H. U. Uduwanage, K. M. S. L. Konara, G. D. R. Mihiranga, S. N. Karunarathna, F. Noordeen, and I. Ekanayake, “Prediction of Dengue Outbreaks in Sri Lanka Using Machine Learning Techniques,” Sri Lanka Journal of Medicine, vol. 34, no. 1, pp. 15-26, 2025.

N. Che Dom, N. A. M. H. Abdullah, R. Dapari, and S. A. Salleh, “Fine-scale predictive modeling of Aedes mosquito abundance and dengue risk indicators using machine learning algorithms with microclimatic variables,” Scientific Reports, vol. 15, no. 37017, 2025.

C. Yi, A. Vajdi, T. Ferdousi, L. W. Cohnstaedt, and C. Scoglio, “PICTUREE-Aedes: A Web Application for Dengue Data Visualization and Case Prediction,” Pathogens, vol. 12, no. 6, 771, 2023.

J. A. Uelmen Jr., A. Clark, J. Palmer, J. Kohler, L. C. Van Dyke, R. Low, C. D. Mapes, and R. M. Carney, “Global mosquito observations dashboard (GMOD): creating a user-friendly web interface fueled by citizen science to monitor invasive and vector mosquitoes,” International Journal of Health Geographics, vol. 22, no. 28, 2023.

P. Chathurangika, S. S. N. Perera, and K. De Silva, “Forecasting dengue outbreaks with uncertainty using seasonal weather patterns,” arXiv preprint arXiv:2401.10295, 2024.

N. Karasinghe, S. Peiris, R. Jayathilaka, and T. Dharmasena, “Forecasting weekly dengue incidence in Sri Lanka: Modified Autoregressive Integrated Moving Average modeling approach,” PLOS ONE, vol. 19, no. 3, e0299953, 2024.

I. T. S. Piyatilake and S. S. N. Perera, “Fuzzy Multidimensional Model to Cluster Dengue Risk in Sri Lanka,” BioMed Research International, vol. 2020, Article ID 2420948, 2020.

S. K. Palo, P. P. Panda, D. Parida, S. T. Malick, and S. Pati, “Remote sensing and GIS-based study to predict risk zones for mosquito-borne diseases in Cuttack district, Odisha, India,” GeoHealth, vol. 9, e2023GH001007.

[9]	 M. A. A. Hamedin, K. I. Musa, and M. R. Sulong, “Time-series decomposition and modeling of dengue cases in Malaysia, 2022–2024: a nationwide observational study,” Osong Public Health and Research Perspectives, 2026. https://doi.org/10.24171/j.phrp.2025.0397

[10] 	X. Chen and P. Moraga, “Assessing dengue forecasting methods: a comparative study of statistical models and machine learning techniques in Rio de Janeiro, Brazil,” Tropical Medicine and Health, vol. 53, no. 32, 2025.

[11] 	Y. V. Exebio-Chepe, J. A. Bravo-Ruiz, and V. A. Tuesta-Monteza, “Comparison of machine learning algorithms for dengue virus (DENV) classification,” Journal of Applied Research and Technology, vol. 22, pp. 729-745, 2024.

[12] 	M. E. Francisco, T. M. Carvajal, and K. Watanabe, “Hybrid Machine Learning Approach to Zero-Inflated Data Improves Accuracy of Dengue Prediction,” PLOS Neglected Tropical Diseases, vol. 18, no. 10, e0012599, 2024. https://doi.org/10.1371/journal.pntd.0012599

[13] 	L. Mardhiyah, Suhartono, M. Raharjo, N. E. Wahyuningsih, and Sulistiyani, “Spatial Clustering and Hotspot Analysis of Dengue Fever in West Java Province, 2020–2024,” KESANS: International Journal of Health and Science, vol. 5, no. 4, pp. 751-760, 2026.

[14]	L. Lin, Y. He, X. Guang, et al., “Spatial pattern assessment of Aedes mosquito bite risk in a subtropical metropolitan area: A case study in Shenzhen,” PLOS Neglected Tropical Diseases, vol. 19, no. 12, e0013843, 2025. https://doi.org/10.1371/journal

[15] 	NASA POWER. Prediction Of Worldwide Energy Resources. https://power.larc.nasa.gov/

[16] 	Climate Hazards Center. CHIRPS: Climate Hazards Group InfraRed Precipitation with Station data. University of California, Santa Barbara. https://www.chc.ucsb.edu/data/chirps

[17] 	WorldPop. Sri Lanka Population Density 2020. https://www.worldpop.org/

[18] 	Global Administrative Areas (GADM). https://gadm.org/

# APPENDIX A

Individuals Contribution to the Project

214099D – Karunarathna R.M.D.R.R.

At present, I am the leader of the Hybrid Spatial Hotspot Detection module whose goal is to locate geographical areas of high risk for transmission of the dengue virus. To build accurate and dynamic risk heatmaps, in my module, I used two stages of spatial modelling, firstly baseline spatial modelling and secondly residual modelling using environmental and demographic data. This is an important consideration in the area of local level vector control and resource allocation.

I have gathered and pre-processed geospatial data of dengue cases, population density layers and environmental raster data till date. I have been able to experiment and implement the baseline spatial analysis methods such as Kernel Density Estimation (KDE) and Global/Local Moran’s I and have started investigating spatial compensation methods to modify the baseline risk surfaces based on climatic and land-use information.

The second part will be dedicated on the development of the residual compensation model for spatial predictions and use advanced techniques such as Geographically Weighted models if appropriate. I will also be creating interactive layers to visualize on the dashboard with Folium and Leaflet.js. In addition, I will guarantee smooth integration of the spatial outputs into the forecasting and classification parts. My goal is to end up with accurate, dynamic maps which will enable officers at the field level to take more effective and targeted dengue prevention measures.

214029P - Bandara H.R.B.G.M.

I am responsible for developing the Hybrid Time-Series Case Forecasting module, which serves as the core quantitative component of the Residual Compensation Modeling Framework for Dengue Risk Prediction. My primary objective is to design and implement a robust two-stage hybrid model that accurately predicts weekly dengue case counts at a fine scale. This module integrates a classical SARIMA/SARIMAX baseline model with a powerful machine learning-based residual compensation mechanism to capture both linear temporal patterns and nonlinear relationships driven by climatic and environmental factors.

So far, I have successfully collected historical weekly dengue incidence data from official sources and integrated it with meteorological variables such as rainfall, temperature, and humidity. I have performed extensive data preprocessing, including missing value imputation, outlier handling, and feature engineering with multiple lagged variables. I have completed time-series decomposition using STL methods, implemented and optimized baseline SARIMA/SARIMAX models, and conducted detailed residual diagnostics. Initial experiments with Random Forest and XGBoost models for residual compensation have shown promising improvements in forecast accuracy compared to standalone baseline models.

In the upcoming phases, I will focus on comprehensive hyperparameter tuning, implementing rolling window time-series cross-validation, and incorporating uncertainty estimation techniques. I will also work on integrating this forecasting module with the classification and spatial modules to ensure seamless data flow within the unified pipeline. My ultimate goal is to deliver highly accurate weekly dengue case forecasts with confidence intervals, enabling public health authorities to make proactive and data-driven decisions for resource allocation and outbreak preparedness.

214140X - Nethma L.H.K.

I have been assigned to the Hybrid Outbreak Risk Classification module, which is trying to predict the chances of dengue outbreaks in the next few weeks. This module is very important for making the predictions into risk intelligence and assigning risk levels as Low, Medium, or High. I am developing a two stage residual compensation model, which is a baseline model to predict baseline probabilities, and a secondary model to correct the prediction errors with contextual indicators and environmental anomalies.

I have done an extensive literature search on the methods and techniques for predicting and classification of risk for dengue outbreaks so far. Performed data preprocessing, feature selection, and feature engineering for classification problems, such as lagged case trends, climate deviation features, and seasonal indicators. Random Forest and XGBoost baseline classification models have been developed and tested. I have also begun to work on the residual compensation layer to get a better handle on the initial risk probabilities and enhance performance of the whole classification.

In the following months, I will be working on advanced techniques like class imbalance handling, probability calibration, and interpretability analysis of SHAP to make the model more transparent and trustworthy. I will also add other variables like population mobility, intervention data etc. to the module to further improve it. I will also make sure the information from this module is well connected with the forecasting module and spatial hotspot module. My ultimate goal is to provide a dependable classification system that allows the health authorities to be alerted in a timely and accurate manner and assist them in making early planning.
