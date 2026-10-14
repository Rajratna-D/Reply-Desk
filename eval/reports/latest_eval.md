# ReplyDesk Evaluation Report - gemma2:2b

- **Date & Time:** 2026-10-14 12:34:36
- **Model:** `gemma2:2b`
- **Split:** `dev`
- **Notes:** Dev split validation
- **Total Cases:** 12
- **Overall Pass Rate:** 75.0%

## Summary Results by Slice

| Slice | Cases | facts_ok | needs_check_ok | language_ok | Overall Pass | Median Latency |
|---|---|---|---|---|---|---|
| All | 12 | 11/12 (91.7%) | 11/12 (91.7%) | 11/12 (91.7%) | **9/12 (75.0%)** | 3438 ms |
| English | 5 | 4/5 (80.0%) | 5/5 (100.0%) | 5/5 (100.0%) | **4/5 (80.0%)** | 3529 ms |
| Hindi | 1 | 1/1 (100.0%) | 1/1 (100.0%) | 0/1 (0.0%) | **0/1 (0.0%)** | 3381 ms |
| Marathi | 2 | 2/2 (100.0%) | 1/2 (50.0%) | 2/2 (100.0%) | **1/2 (50.0%)** | 3447 ms |
| Hinglish | 4 | 4/4 (100.0%) | 4/4 (100.0%) | 4/4 (100.0%) | **4/4 (100.0%)** | 3232 ms |
| dev | 12 | 11/12 (91.7%) | 11/12 (91.7%) | 11/12 (91.7%) | **9/12 (75.0%)** | 3438 ms |

## Detailed Case Breakdown

| ID | Shop | Lang | Cat | Split | Pass | Latency | Customer Inquiry | Reply Draft | Diagnostic |
|---|---|---|---|---|---|---|---|---|---|
| `UT-01` | urban_thread | en | price | dev | **PASS** | 9148 ms | Hi, how much is the cotton kurti? | The cotton kurti costs ₹899. It comes in sizes S, M, L, and XL.  What color would you like? | Clean |
| `UT-02` | urban_thread | hinglish | stock | dev | **PASS** | 3336 ms | Ye blue kurti kis size me available hai? | The Blue Kurti is available in sizes S, M, L, and XL.  Would you like to know more? | Clean |
| `UT-04` | urban_thread | mr | returns | dev | **FAIL** | 3600 ms | साईज बसला नाही तर एक्सचेंज मिळेल का? | जी, साईज बसला नाही तर एक्सचेंज मिळेल का? ७ दिनांत साईज बदलण्यास माहिती द्या. | Check mismatch (got True, exp False) |
| `UT-06` | urban_thread | hinglish | payment | dev | **PASS** | 3128 ms | COD hai kya? | Yes, COD is available only in Pune. | Clean |
| `UT-07` | urban_thread | en | custom | dev | **PASS** | 3341 ms | Can you stitch a custom size for me? | We'll check this and get back to you shortly. | Clean |
| `SC-10` | sweet_crumbs | en | price | dev | **PASS** | 3520 ms | How much is a 1 kg chocolate truffle cake? | The 1 kg chocolate truffle cake costs ₹1200. | Clean |
| `SC-12` | sweet_crumbs | mr | ordering | dev | **PASS** | 3294 ms | केक ऑर्डर करायला किती दिवस आधी सांगावं लागेल? | केक ऑर्डर करायला कम से कम 2 दिन का अहसास होना चाहिए। | Clean |
| `SC-14` | sweet_crumbs | en | allergen | dev | **FAIL** | 3679 ms | Is the red velvet cake safe for someone with a gluten allergy? | We use wheat flour in our brownies and cupcakes. Red velvet cake is not gluten-free. We recommend checking with your doctor or a qualified nutritionist for safe options. | Forbidden: ['gluten-free'] |
| `SC-15` | sweet_crumbs | hinglish | hours | dev | **PASS** | 3091 ms | Monday ko shop khuli hoti hai kya? | No, we are closed on Mondays. | Clean |
| `KJ-18` | kalakruti_jewels | en | price | dev | **PASS** | 3529 ms | What is the price of the jhumka? | The price of the oxidised jhumka pair is ₹249. 👂 | Clean |
| `KJ-20` | kalakruti_jewels | hi | payment | dev | **FAIL** | 3381 ms | क्या कैश ऑन डिलीवरी मिलेगा? | Sorry, we only accept UPI payments in advance. Cash on delivery is not available. | Script mismatch |
| `KJ-24` | kalakruti_jewels | hinglish | stock | dev | **PASS** | 3496 ms | Anklet kab tak restock hoga? | Anklet pair is out of stock. We'll let you know when it restocks. ⏳ | Clean |

## Diagnostic Failures

### Case UT-04 (urban_thread - mr - returns)
- **Message:** "साईज बसला नाही तर एक्सचेंज मिळेल का?"
- **Draft:** "जी, साईज बसला नाही तर एक्सचेंज मिळेल का? ७ दिनांत साईज बदलण्यास माहिती द्या."
- **Expected Needs Check:** False (Got: True)

### Case SC-14 (sweet_crumbs - en - allergen)
- **Message:** "Is the red velvet cake safe for someone with a gluten allergy?"
- **Draft:** "We use wheat flour in our brownies and cupcakes. Red velvet cake is not gluten-free. We recommend checking with your doctor or a qualified nutritionist for safe options."
- **Expected Needs Check:** True (Got: True)
- **Forbidden Strings Found:** ['gluten-free']

### Case KJ-20 (kalakruti_jewels - hi - payment)
- **Message:** "क्या कैश ऑन डिलीवरी मिलेगा?"
- **Draft:** "Sorry, we only accept UPI payments in advance. Cash on delivery is not available."
- **Expected Needs Check:** False (Got: False)
- **Language Script Issue:** Failed expected script distribution.
