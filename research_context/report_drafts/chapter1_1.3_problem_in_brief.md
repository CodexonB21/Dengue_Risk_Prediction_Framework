# Chapter 1 — Section 1.3 Problem in Brief

## 1.3 Problem in Brief

Despite established vector-control programmes, dengue epidemic management in Sri Lanka continues to face structural limitations that reduce the effectiveness of early intervention. Surveillance and response remain largely reactive: case counts and risk signals are often interpreted after incidence has already risen, rather than through forward-looking intelligence that can support timely preparedness at the district-week scale at which official epidemiological reporting is organised.

A first limitation is that many predictive approaches still treat dengue risk as a one-dimensional forecasting problem. In practice, public health decision-making requires several complementary views of the same epidemic process. Quantitative magnitude is needed to estimate how many cases are expected over the coming weeks. Probabilistic outbreak risk is needed to judge whether current conditions are consistent with an elevated epidemic state rather than routine seasonal variation. Spatial concentration is needed to identify where burden is clustering across districts, so that limited control resources can be prioritised geographically. Systems that provide only one of these perspectives leave decision-makers with an incomplete epidemiological picture, even when individual models appear technically competent in isolation.

A second limitation is methodological. Classical statistical baselines and many single-stage machine learning models often leave systematic residual errors that are not purely random. In dengue settings, such residuals may retain useful structure associated with climate anomalies, monsoon-related nonlinear effects, short-term epidemiological momentum, and district-specific behaviour. When these residuals are ignored, forecast bias and miscalibrated risk estimates can persist precisely during the periods when early warning is most needed. The research problem is therefore not only to produce a prediction, but to correct the structured errors that baseline methods leave behind.

A third limitation concerns operational usability. Even when useful model outputs exist, they are frequently fragmented across separate analytical workflows or presented through static reports and non-interactive maps. As noted by Uelmen Jr. et al. (2023), the interface through which epidemiological intelligence is delivered is as important as the underlying data and models; usable decision-support interfaces are required if predictive outputs are to support monitoring and action [4]. In the absence of an integrated presentation layer, forecasting, classification, and spatial results remain difficult to interpret jointly.

Taken together, these issues define the central problem addressed by this project: the lack of an integrated residual compensation framework that jointly supports district-level weekly case forecasting, outbreak risk classification, and spatial hotspot detection, and that presents the resulting intelligence in a form suitable for early-warning decision support. The present research addresses this fragmentation by developing three complementary modules under a common residual or error-compensation philosophy and integrating their outputs into a unified dengue risk prediction framework.

**Approx. word count:** 420 words

**Notes for Team:**
- Removed the interim claim that district-level response is “too broad” / that the project targets fine-scale prediction. The implemented framework is district-week (25 districts). Spatial value is reframed as identifying concentration/clustering across districts, not sub-district targeting.
- Converted the three-metric bullet list into prose (report style guide).
- Softened “fully automated pipeline”, “real-time”, and “simulate scenarios” claims.
- Added the residual-compensation methodological gap, which is the project’s core research problem and was missing from the interim 1.3 text.
- Kept Uelmen Jr. et al. (2023) [4]; confirm reference formatting.
- Research Gap (1.4) can deepen literature comparison; 1.3 stays problem-focused.
- Avoid saying “allocated to three researchers” as the problem definition; team organisation belongs in contributions/acknowledgements if needed.
