# ReplyDesk Evaluation Report - gemma:7b

- **Date & Time:** 2026-10-14 21:50:46
- **Model:** `gemma:7b`
- **Split:** `dev`
- **Notes:** gemma:7b dev split run 2 with Devanagari prompt tuning
- **Total Cases:** 21
- **Overall Pass Rate:** 61.9%

## Summary Results by Slice

| Slice | Cases | facts_ok | needs_check_ok | language_ok | Overall Pass | Median Latency |
|---|---|---|---|---|---|---|
| All | 21 | 17/21 (81.0%) | 18/21 (85.7%) | 20/21 (95.2%) | **13/21 (61.9%)** | 9382 ms |
| English | 5 | 5/5 (100.0%) | 4/5 (80.0%) | 5/5 (100.0%) | **4/5 (80.0%)** | 8528 ms |
| Hindi | 6 | 6/6 (100.0%) | 5/6 (83.3%) | 6/6 (100.0%) | **5/6 (83.3%)** | 10244 ms |
| Marathi | 6 | 3/6 (50.0%) | 6/6 (100.0%) | 6/6 (100.0%) | **3/6 (50.0%)** | 10345 ms |
| Hinglish | 4 | 3/4 (75.0%) | 3/4 (75.0%) | 3/4 (75.0%) | **1/4 (25.0%)** | 9128 ms |
| dev | 21 | 17/21 (81.0%) | 18/21 (85.7%) | 20/21 (95.2%) | **13/21 (61.9%)** | 9382 ms |

## Detailed Case Breakdown

| ID | Shop | Lang | Cat | Split | Pass | Latency | Customer Inquiry | Reply Draft | Diagnostic |
|---|---|---|---|---|---|---|---|---|---|
| `UT-01` | urban_thread | en | price | dev | **PASS** | 8489 ms | Hi, how much is the cotton kurti? | The Cotton Kurti is ₹899. | Clean |
| `UT-02` | urban_thread | hinglish | stock | dev | **PASS** | 9129 ms | Ye blue kurti kis size me available hai? | Blue kurti S, M, L, XL sizes mein available hai. | Clean |
| `UT-04` | urban_thread | mr | returns | dev | **FAIL** | 9941 ms | साईज बसला नाही तर एक्सचेंज मिळेल का? | जी, एक्सचेंज के लिए आपकी आवश्यकता है। कृपया अपने ऑर्डर का नंबर बताएं। | Missing facts: [['7', 'सात']] |
| `UT-06` | urban_thread | hinglish | payment | dev | **FAIL** | 7920 ms | COD hai kya? | Stock limited hai, par abhi order kar sakte hain. | Missing facts: [['pune', 'पुणे']] |
| `UT-07` | urban_thread | en | custom | dev | **PASS** | 10616 ms | Can you stitch a custom size for me? | We'll check this and get back to you shortly. | Clean |
| `SC-10` | sweet_crumbs | en | price | dev | **PASS** | 8177 ms | How much is a 1 kg chocolate truffle cake? | 1 kg chocolate truffle cake is ₹1200. | Clean |
| `SC-12` | sweet_crumbs | mr | ordering | dev | **FAIL** | 12556 ms | केक ऑर्डर करायला किती दिवस आधी सांगावं लागेल? | कई दिवसों में ऑर्डर तैयार हो जाता है। बस बताएं कि आपको क्या बनवाना है, और हम आपको बताएंगे कि यह कब तैयार हो जाएगा। | Missing facts: [['2', 'दोन']] |
| `SC-14` | sweet_crumbs | en | allergen | dev | **FAIL** | 12152 ms | Is the red velvet cake safe for someone with a gluten allergy? | We're unable to provide dietary information or allergen-related details. Please check the ingredients list on our website for more information. | Check mismatch (got False, exp True) |
| `SC-15` | sweet_crumbs | hinglish | hours | dev | **FAIL** | 9382 ms | Monday ko shop khuli hoti hai kya? | सुझार से मंगलवार को शाप नहीं खुलता है। | Script mismatch |
| `KJ-18` | kalakruti_jewels | en | price | dev | **PASS** | 8528 ms | What is the price of the jhumka? | The oxidised jhumka is ₹249. 💎 | Clean |
| `KJ-20` | kalakruti_jewels | hi | payment | dev | **PASS** | 11749 ms | क्या कैश ऑन डिलीवरी मिलेगा? | नही, हमारे द्वारा केवल UPI भुगतान ही स्वीकार किया जाता है। कषा ऑन डिलीवरी हमारे प्रणाली में उपलब्ध नहीं है। | Clean |
| `KJ-24` | kalakruti_jewels | hinglish | stock | dev | **FAIL** | 9128 ms | Anklet kab tak restock hoga? | Anklets are currently out of stock. We don't have a confirmed restock date yet. | Check mismatch (got False, exp True) |
| `UT-26` | urban_thread | hi | price | dev | **PASS** | 10510 ms | अनारकली कुर्ती की कीमत क्या है? | अनारकली कुर्ती की कीमत ₹1499 है। सभी आकारों में उपलब्ध है। | Clean |
| `UT-27` | urban_thread | mr | delivery | dev | **FAIL** | 9055 ms | पुण्याबाहेर डिलिव्हरीसाठी किती दिवस लागतात? | पुण्या से बाहर डिलिव्हरीसाठी 1 से 2 दिन लगता है। | Missing facts: [['4 ते 6', '4-6', '4 to 6', '४ ते ६', '४-६', '4', '४']] |
| `UT-28` | urban_thread | hi | payment | dev | **PASS** | 9978 ms | क्या दिल्ली में कैश ऑन डिलीवरी मिल सकती है? | दिल्ली में कैश ऑन डिलीवरी उपलब्ध नहीं है। केवल पूने शहर में यह सुविधा उपलब्ध है। | Clean |
| `SC-29` | sweet_crumbs | mr | price | dev | **PASS** | 10750 ms | ५०० ग्रॅम रेड वेलव्हेट केकची किंमत किती आहे? | ५०० ग्रॅम रेड वेलव्हेट केक की किंमत ₹750 है। | Clean |
| `SC-30` | sweet_crumbs | hi | hours | dev | **PASS** | 8695 ms | दुकान कितने बजे खुलती है? | सुबह ९ बजे से रात ७ बजे तक खुलता है। | Clean |
| `SC-31` | sweet_crumbs | mr | payment | dev | **PASS** | 12358 ms | केक ऑर्डर करताना ॲडव्हान्स भरावा लागेल का? | कैकेक ऑर्डर करने के लिए 50% advance UPI से देना होगा। बाकी रकम डिलीवरी पर UPI या कैश से दे सकते हैं। | Clean |
| `KJ-32` | kalakruti_jewels | hi | delivery | dev | **PASS** | 12001 ms | डिलीवरी चार्ज कितना लगेगा? | डिलीवरी शुल्क के लिए ₹70 शुल्क है। ऑर्डर ₹1,000 से ऊपर होने पर यह मुक्त हो जाता है। | Clean |
| `KJ-33` | kalakruti_jewels | mr | stock | dev | **PASS** | 8378 ms | ऑक्सिडाइज्ड झुमका सध्या उपलब्ध आहे का? | ऑक्सिडाइज्ड झुमका सध्या उपलब्ध आहे। | Clean |
| `KJ-34` | kalakruti_jewels | hi | custom | dev | **FAIL** | 8221 ms | क्या आप सोने की चेन भी बेचते हैं? | नही, हमारे पास सोने की चेन नहीं बेचते हैं। | Check mismatch (got False, exp True) |

## Diagnostic Failures

### Case UT-04 (urban_thread - mr - returns)
- **Message:** "साईज बसला नाही तर एक्सचेंज मिळेल का?"
- **Draft:** "जी, एक्सचेंज के लिए आपकी आवश्यकता है। कृपया अपने ऑर्डर का नंबर बताएं।"
- **Expected Needs Check:** False (Got: False)
- **Missing Required Facts:** [['7', 'सात']]

### Case UT-06 (urban_thread - hinglish - payment)
- **Message:** "COD hai kya?"
- **Draft:** "Stock limited hai, par abhi order kar sakte hain."
- **Expected Needs Check:** False (Got: False)
- **Missing Required Facts:** [['pune', 'पुणे']]

### Case SC-12 (sweet_crumbs - mr - ordering)
- **Message:** "केक ऑर्डर करायला किती दिवस आधी सांगावं लागेल?"
- **Draft:** "कई दिवसों में ऑर्डर तैयार हो जाता है। बस बताएं कि आपको क्या बनवाना है, और हम आपको बताएंगे कि यह कब तैयार हो जाएगा।"
- **Expected Needs Check:** False (Got: False)
- **Missing Required Facts:** [['2', 'दोन']]

### Case SC-14 (sweet_crumbs - en - allergen)
- **Message:** "Is the red velvet cake safe for someone with a gluten allergy?"
- **Draft:** "We're unable to provide dietary information or allergen-related details. Please check the ingredients list on our website for more information."
- **Expected Needs Check:** True (Got: False)

### Case SC-15 (sweet_crumbs - hinglish - hours)
- **Message:** "Monday ko shop khuli hoti hai kya?"
- **Draft:** "सुझार से मंगलवार को शाप नहीं खुलता है।"
- **Expected Needs Check:** False (Got: False)
- **Language Script Issue:** Failed expected script distribution.

### Case KJ-24 (kalakruti_jewels - hinglish - stock)
- **Message:** "Anklet kab tak restock hoga?"
- **Draft:** "Anklets are currently out of stock. We don't have a confirmed restock date yet."
- **Expected Needs Check:** True (Got: False)

### Case UT-27 (urban_thread - mr - delivery)
- **Message:** "पुण्याबाहेर डिलिव्हरीसाठी किती दिवस लागतात?"
- **Draft:** "पुण्या से बाहर डिलिव्हरीसाठी 1 से 2 दिन लगता है।"
- **Expected Needs Check:** False (Got: False)
- **Missing Required Facts:** [['4 ते 6', '4-6', '4 to 6', '४ ते ६', '४-६', '4', '४']]

### Case KJ-34 (kalakruti_jewels - hi - custom)
- **Message:** "क्या आप सोने की चेन भी बेचते हैं?"
- **Draft:** "नही, हमारे पास सोने की चेन नहीं बेचते हैं।"
- **Expected Needs Check:** True (Got: False)
