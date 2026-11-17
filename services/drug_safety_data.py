"""
Authoritative clinical pharmacology and safety reference dictionaries:
  - MOIETY_CHINESE_NAMES: Active moiety Chinese and trade name translations
  - MOIETY_DRUG_CLASSES: Pharmacological and therapeutic drug class mappings
  - MOIETY_MONOTHERAPY_DOSES: Monotherapy starting and maximum safe daily doses
  - MOIETY_CLINICAL_REMARKS: Dosing guidance, organ dose adjustment, monitoring, and warnings
"""

from typing import Any, Dict

MOIETY_CHINESE_NAMES: Dict[str, str] = {
    "VALSARTAN": "Valsartan (纈沙坦)",
    "AMLODIPINE": "Amlodipine (脈優 / 氨氯地平)",
    "TELMISARTAN": "Telmisartan (替米沙坦)",
    "LOSARTAN": "Losartan (洛沙坦)",
    "OLMESARTAN": "Olmesartan (歐美沙坦)",
    "IRBESARTAN": "Irbesartan (厄貝沙坦)",
    "CANDESARTAN": "Candesartan (肯得沙坦)",
    "SACUBITRIL": "Sacubitril (沙庫巴曲)",
    "HYDROCHLOROTHIAZIDE": "Hydrochlorothiazide (氫氯噻嗪 / 噻嗪利尿劑)",
    "METFORMIN": "Metformin (雙胍類 / 二甲雙胍)",
    "SITAGLIPTIN": "Sitagliptin (席他列汀 / 捷諾維)",
    "LINAGLIPTIN": "Linagliptin (利拉利汀 / 糖漸平)",
    "EMPAGLIFLOZIN": "Empagliflozin (恩格列淨 / 恩排糖)",
    "DAPAGLIFLOZIN": "Dapagliflozin (達格列淨 / 福適佳)",
    "GLIMEPIRIDE": "Glimepiride (格列美脲 / 瑪爾胰)",
    "GLICLAZIDE": "Gliclazide (格列齊特 / 岱蜜克龍)",
    "PIOGLITAZONE": "Pioglitazone (吡格列酮 / 愛妥糖)",
    "ATORVASTATIN": "Atorvastatin (立普妥 / 阿托伐他汀)",
    "ROSUVASTATIN": "Rosuvastatin (冠脂妥 / 羅素他汀)",
    "FENOFIBRATE": "Fenofibrate (微粒化非諾貝特)",
    "EZETIMIBE": "Ezetimibe (依折麥布 / 怡妥)",
    "ACETAMINOPHEN": "Acetaminophen (普拿疼 / 乙醯胺酚)",
    "TRAMADOL": "Tramadol (曲馬多 / 妥美多)",
    "CODEINE": "Codeine (可待因)",
    "DICLOFENAC": "Diclofenac (雙氯芬酸 / 伏塔蓮)",
    "IBUPROFEN": "Ibuprofen (布洛芬 / 依普芬)",
    "CELECOXIB": "Celecoxib (希樂葆 / 塞來昔布)",
    "ASPIRIN": "Aspirin (阿斯匹靈)",
    "CLOPIDOGREL": "Clopidogrel (保栓通 / 氯吡格雷)",
    "WARFARIN": "Warfarin (可邁丁 / 華法林)",
    "BISOPROLOL": "Bisoprolol (康肯 / 畢索洛爾)",
    "CARVEDILOL": "Carvedilol (達利全 / 卡維地洛)",
    "FUROSEMIDE": "Furosemide (來適泄 / 呋塞米)",
    "SPIRONOLACTONE": "Spironolactone (歐達通 / 螺內酯)",
    "FAMOTIDINE": "Famotidine (法莫替丁)",
    "OMEPRAZOLE": "Omeprazole (奧美拉唑)",
    "ESOMEPRAZOLE": "Esomeprazole (耐適恩 / 埃索美拉唑)",
    "AMOXICILLIN": "Amoxicillin (安莫西林)",
    "CLAVULANATE": "Clavulanate (克拉維酸)",
    "CLAVULANIC ACID": "Clavulanate (克拉維酸)",
    "CEPHALEXIN": "Cephalexin (第一代頭孢菌素)",
    "LEVOFLOXACIN": "Levofloxacin (可樂必妥 / 左氧氟沙星)",
    "PREDNISOLONE": "Prednisolone (普立朗 / 潑尼松龍)",
    "CALCIUM ACETATE": "Calcium Acetate (醋酸鈣 / 降磷劑)",
    "MEQUITAZINE": "Mequitazine (竹林妥 / 美喹他嗪)",
    "CETIRIZINE": "Cetirizine (勝克敏 / 西替利嗪)",
}

# Drug classes for active moieties
MOIETY_DRUG_CLASSES: Dict[str, str] = {
    "VALSARTAN": "ARB 血管收縮素受體阻斷劑",
    "AMLODIPINE": "二氫吡啶類 (DHP) 鈣離子通道阻斷劑",
    "TELMISARTAN": "ARB 血管收縮素受體阻斷劑",
    "LOSARTAN": "ARB 血管收縮素受體阻斷劑",
    "OLMESARTAN": "ARB 血管收縮素受體阻斷劑",
    "IRBESARTAN": "ARB 血管收縮素受體阻斷劑",
    "CANDESARTAN": "ARB 血管收縮素受體阻斷劑",
    "SACUBITRIL": "腦啡肽酶抑制劑 (Neprilysin Inhibitor)",
    "HYDROCHLOROTHIAZIDE": "噻嗪類利尿劑 (Thiazide Diuretic)",
    "METFORMIN": "雙胍類胰島素敏感劑 (Biguanide)",
    "SITAGLIPTIN": "DPP-4 抑制劑 (Dipeptidyl Peptidase-4)",
    "LINAGLIPTIN": "DPP-4 抑制劑 (Dipeptidyl Peptidase-4)",
    "EMPAGLIFLOZIN": "SGLT2 抑制劑 (鈉-葡萄糖轉運蛋白2抑制劑)",
    "DAPAGLIFLOZIN": "SGLT2 抑制劑 (鈉-葡萄糖轉運蛋白2抑制劑)",
    "GLIMEPIRIDE": "第二代磺醯尿素類 (Sulfonylurea)",
    "GLICLAZIDE": "第二代磺醯尿素類 (Sulfonylurea)",
    "PIOGLITAZONE": "TZD 類胰島素增敏劑 (Thiazolidinedione)",
    "ATORVASTATIN": "HMG-CoA 還原酶抑制劑 (Statin)",
    "ROSUVASTATIN": "HMG-CoA 還原酶抑制劑 (Statin)",
    "FENOFIBRATE": "纖維酸衍生物降三酸甘油酯劑 (Fibrate)",
    "EZETIMIBE": "小腸膽固醇吸收抑制劑",
    "ACETAMINOPHEN": "中樞乙醯胺酚解熱鎮痛劑",
    "TRAMADOL": "中樞微弱類鴉片止痛劑",
    "CODEINE": "類鴉片止痛止咳劑",
    "DICLOFENAC": "NSAID 非類固醇消炎止痛藥",
    "IBUPROFEN": "NSAID 非類固醇消炎止痛藥",
    "CELECOXIB": "選擇性 COX-2 抑制劑",
    "ASPIRIN": "不可逆 COX-1 抗血小板劑",
    "CLOPIDOGREL": "P2Y12 受體拮抗劑 (抗血小板)",
    "WARFARIN": "維生素 K 拮抗劑 (口服抗凝血)",
    "BISOPROLOL": "高選擇性 Beta-1 腎上腺素受體阻斷劑",
    "CARVEDILOL": "非選擇性 Beta 兼具 Alpha-1 阻斷劑",
    "FUROSEMIDE": "亨利氏環利尿劑 (Loop Diuretic)",
    "SPIRONOLACTONE": "醛固酮受體拮抗保鉀利尿劑 (MRA)",
    "FAMOTIDINE": "H2 受體拮抗抑酸劑",
    "OMEPRAZOLE": "質子泵抑制劑 (PPI)",
    "ESOMEPRAZOLE": "S-異構物質子泵抑制劑 (PPI)",
    "AMOXICILLIN": "廣效青黴素抗生素 (Aminopenicillin)",
    "CLAVULANATE": "Beta-內醯胺酶抑制劑 (Beta-lactamase inhibitor)",
    "CLAVULANIC ACID": "Beta-內醯胺酶抑制劑 (Beta-lactamase inhibitor)",
    "CEPHALEXIN": "第一代口服頭孢菌素 (Cephalosporin)",
    "LEVOFLOXACIN": "第三代 Fluoroquinolone 廣效抗生素",
    "PREDNISOLONE": "中效口服糖皮質素類固醇",
}

# Monotherapy standard starting doses
MOIETY_MONOTHERAPY_DOSES: Dict[str, str] = {
    "VALSARTAN": "常用 80 ~ 160 mg 每日一次 (心衰 40 mg BID)",
    "AMLODIPINE": "常規 5 mg 每日一次 (年長/肝弱起始 2.5 mg)",
    "TELMISARTAN": "常用 40 ~ 80 mg 每日一次",
    "LOSARTAN": "常用 50 ~ 100 mg 每日一次",
    "OLMESARTAN": "常用 20 ~ 40 mg 每日一次",
    "SACUBITRIL": "與 Valsartan 1:1 莫耳比複方使用 (如 24/26 mg 或 49/51 mg BID)",
    "HYDROCHLOROTHIAZIDE": "降壓常用 12.5 ~ 25 mg 每日一次早晨服用",
    "METFORMIN": "起始 500 mg 每日 1~2 次隨餐，常用維持 1000~2000 mg/天",
    "SITAGLIPTIN": "標準 100 mg 每日一次 (eGFR 30-44: 50mg, <30: 25mg)",
    "LINAGLIPTIN": "固定 5 mg 每日一次 (腎功能不全者免調)",
    "EMPAGLIFLOZIN": "常用 10 ~ 25 mg 每日一次早晨服用",
    "DAPAGLIFLOZIN": "常用 10 mg 每日一次早晨服用",
    "GLIMEPIRIDE": "常用 1 ~ 4 mg 每日一次餐前服用",
    "ATORVASTATIN": "常用 10 ~ 40 mg 每日一次 (早晚皆可)",
    "ROSUVASTATIN": "常用 5 ~ 20 mg 每日一次",
    "EZETIMIBE": "常用 10 mg 每日一次",
    "ACETAMINOPHEN": "單次 500 mg 每 4~6 小時一次，必要時服用",
    "TRAMADOL": "單次 50 mg 每 4~6 小時一次，必要時服用",
    "ASPIRIN": "心血管預防維持 100 mg 每日一次飯後",
    "CLOPIDOGREL": "維持 75 mg 每日一次",
    "AMOXICILLIN": "常用 500 mg TID 或 875 mg BID",
    "CLAVULANATE": "常與 Amoxicillin 依 4:1 或 7:1 比例併服",
}

# Clinical warnings & renal notes for components
MOIETY_CLINICAL_REMARKS: Dict[str, Dict[str, str]] = {
    "VALSARTAN": {
        "warning": "懷孕嚴格禁用 (FDA 黑框警語：胎兒毒性/腎發育不全)；需注意高血鉀",
        "renal": "eGFR < 30 mL/min 慎用，加強監測血鉀與肌酸酐"
    },
    "AMLODIPINE": {
        "warning": "超量顯著增加周邊下肢水腫、嚴重低血壓與頭暈風險",
        "renal": "各級腎功能不全者皆無需調整劑量"
    },
    "TELMISARTAN": {
        "warning": "懷孕嚴格禁用 (FDA 黑框警語：胎兒毒性)；防高血鉀",
        "renal": "輕中度免調整；重度腎衰或透析患者起始以 20 mg 為原則"
    },
    "LOSARTAN": {
        "warning": "懷孕嚴格禁用 (黑框警語)；高血鉀風險",
        "renal": "重度腎衰竭或血容積不足者由 25 mg 起始"
    },
    "SACUBITRIL": {
        "warning": "嚴禁與 ACEI 併用 (必須停用 ACEI 滿 36 小時避免血管性水腫)",
        "renal": "eGFR < 30 mL/min 起始劑量減半為 24/26 mg BID"
    },
    "HYDROCHLOROTHIAZIDE": {
        "warning": "注意低血鉀、低血鈉、高尿酸及高血糖；對磺胺藥過敏者禁用",
        "renal": "eGFR < 30 mL/min 利尿療效降低，宜改用環利尿劑"
    },
    "METFORMIN": {
        "warning": "eGFR < 30 mL/min 嚴格禁用 (致死性乳酸中毒 MALA 風險)",
        "renal": "eGFR 45-59 上限 2000mg；eGFR 30-44 上限 1000mg；eGFR < 30 絕對禁用"
    },
    "SITAGLIPTIN": {
        "warning": "注意胰臟炎風險；需依 eGFR 腎功能階梯調整劑量",
        "renal": "eGFR ≥ 45: 100mg；eGFR 30-44: 50mg；eGFR < 30: 25mg"
    },
    "LINAGLIPTIN": {
        "warning": "低血糖風險低；體重中性",
        "renal": "各階段腎衰竭 (含洗腎透析) 均不需調整劑量"
    },
    "EMPAGLIFLOZIN": {
        "warning": "需補充足夠水分；防生殖泌尿道感染與正常血糖酮酸中毒 (eDKA)",
        "renal": "eGFR < 20 mL/min 不建議起始治療；心衰/CKD 可維持 10mg"
    },
    "ACETAMINOPHEN": {
        "warning": "每日上限 4,000 mg (肝病/長者 2,000 mg)；超量具嚴重急性肝衰竭毒性",
        "renal": "常規劑量無需調整；避免長期大劑量併用 NSAID"
    },
    "TRAMADOL": {
        "warning": "注意暈眩、噁心、便秘、嗜睡與癲癇發作風險；具藥物成癮潛力",
        "renal": "CrCl < 30 mL/min 給藥間隔應延長為每 12 小時一次，每日上限 200 mg"
    }
}

# Standard adult max daily fallback limits
FALLBACK_LIMITS: Dict[str, float] = {
    "VALSARTAN": 320.0,
    "AMLODIPINE": 10.0,
    "TELMISARTAN": 80.0,
    "LOSARTAN": 100.0,
    "OLMESARTAN": 40.0,
    "IRBESARTAN": 300.0,
    "CANDESARTAN": 32.0,
    "SACUBITRIL": 194.0,
    "HYDROCHLOROTHIAZIDE": 50.0,
    "METFORMIN": 2550.0,
    "SITAGLIPTIN": 100.0,
    "LINAGLIPTIN": 5.0,
    "EMPAGLIFLOZIN": 25.0,
    "DAPAGLIFLOZIN": 10.0,
    "GLIMEPIRIDE": 8.0,
    "GLICLAZIDE": 120.0,
    "PIOGLITAZONE": 45.0,
    "ATORVASTATIN": 80.0,
    "ROSUVASTATIN": 40.0,
    "FENOFIBRATE": 200.0,
    "EZETIMIBE": 10.0,
    "ACETAMINOPHEN": 4000.0,
    "TRAMADOL": 400.0,
    "CODEINE": 240.0,
    "DICLOFENAC": 150.0,
    "IBUPROFEN": 2400.0,
    "CELECOXIB": 400.0,
    "ASPIRIN": 325.0,
    "CLOPIDOGREL": 75.0,
    "WARFARIN": 10.0,
    "BISOPROLOL": 20.0,
    "CARVEDILOL": 100.0,
    "FUROSEMIDE": 160.0,
    "SPIRONOLACTONE": 100.0,
    "FAMOTIDINE": 80.0,
    "OMEPRAZOLE": 40.0,
    "ESOMEPRAZOLE": 40.0,
    "AMOXICILLIN": 3000.0,
    "CLAVULANATE": 500.0,
    "CLAVULANIC ACID": 500.0,
    "CEPHALEXIN": 4000.0,
    "LEVOFLOXACIN": 750.0,
    "PREDNISOLONE": 80.0,
    "CALCIUM ACETATE": 8000.0,
    "MEQUITAZINE": 10.0,
    "CETIRIZINE": 10.0
}

# Authoritative outpatient clinical dosing knowledge dictionary (Taiwan & international guidelines)
CLINICAL_DOSING_KB: Dict[str, Dict[str, str]] = {
    # ==================== 固定劑量複方 (Fixed-Dose Combinations) ====================
    "valsartan + amlodipine": {
        "starting_dose": "複方起始：每日 1 錠 (隨餐或空腹)；依處方規格 (5/80 mg) 每日一次",
        "max_daily_dose": "複方每日上限 1 錠 (最高規格 10/320 mg；個別上限：Amlodipine 10 mg/天、Valsartan 320 mg/天)",
        "timing": "每日一次固定時間服用，早晨隨餐或空腹服用為佳",
        "titration": "建議治療 1~2 週後依血壓監測滴定規格 (5/80 mg -> 5/160 mg -> 10/160 mg 至最高 10/320 mg)。年長體弱或肝功能障礙者建議由含 Amlodipine 2.5 mg 之單方或低劑量評估起始。",
        "summary": "本品為【ARB 血管收縮素受體阻斷劑 (Valsartan)】與【二氫吡啶類鈣離子通道阻斷劑 (Amlodipine)】之固定劑量複方降壓藥 (FDC)。兩者機轉互補可顯著增強降壓療效，並減少單用高劑量鈣離子阻斷劑之水腫反應。各主成分每日安全上限分別為：Amlodipine 10 mg/天、Valsartan 320 mg/天。黑框警語：孕婦禁用 (Valsartan 胎兒毒性)。"
    },
    "sitagliptin + metformin": {
        "starting_dose": "依目前個別劑量起始，常用規格 50/500 mg 或 50/850 mg 每日兩次隨餐服用",
        "max_daily_dose": "每日兩次，每日最大 100/2000 mg (Sitagliptin 100 mg / Metformin 2000 mg)",
        "timing": "隨餐或飯後立即服用 (以減少胃腸道腹瀉不適)",
        "titration": "依血糖監測與胃腸道耐受性逐步遞增 Metformin 劑量至每日 2000 mg",
        "summary": "DPP-4 抑制劑 (Sitagliptin) 併用雙胍類 (Metformin) 複方降血糖藥。eGFR < 30 mL/min 或重度肝硬化嚴格禁用 (預防致死性乳酸中毒 MALA)。"
    },
    "tramadol + acetaminophen": {
        "starting_dose": "每次 1~2 錠，每 4~6 小時一次，必要時服用 (PRN)",
        "max_daily_dose": "每日最多 8 錠 (含 Tramadol 300 mg / Acetaminophen 2600 mg；一般 Acetaminophen 單日上限 4000 mg)",
        "timing": "疼痛發作時飯後服用，不可與酒精併用",
        "titration": "依疼痛嚴重度調整，單次不超過 2 錠，最短間隔 4~6 小時",
        "summary": "弱類鴉片 (Tramadol) 與解熱鎮痛 (Acetaminophen) 複方止痛劑。具加乘中樞止痛作用。注意暈眩、噁心、便秘及嗜睡；嚴防與其他乙醯胺酚藥物重複蓄積過量造成肝毒性。"
    },
    "sacubitril + valsartan": {
        "starting_dose": "常規起始 49/51 mg 每日兩次 (早晚各一錠)；先前未使用 ACEI/ARB 或低劑量者起始 24/26 mg 每日兩次",
        "max_daily_dose": "97/103 mg 每日兩次 (每日總量 Sacubitril 194 mg + Valsartan 206 mg)",
        "timing": "早晚固定時間服用，可隨餐或空腹",
        "titration": "每 2~4 週倍增至目標維持劑量 97/103 mg BID。轉換自 ACEI 必須停藥滿 36 小時避免血管性水腫。",
        "summary": "ARNI 類心衰竭指引首選藥物 (Sacubitril/Valsartan)。顯著降低心血管死亡與心衰住院風險。黑框警語：孕婦禁用；需密切監測血壓、血鉀及肌酸酐。"
    },
    "telmisartan + amlodipine": {
        "starting_dose": "每日 1 錠 (常用規格 40/5 mg 或 80/5 mg 每日一次)",
        "max_daily_dose": "複方每日上限 1 錠 (最高規格 80/10 mg；Amlodipine 上限 10 mg/天、Telmisartan 上限 80 mg/天)",
        "timing": "每日一次固定時間服用，可隨餐或空腹",
        "titration": "給藥 2~4 週後依血壓監測滴定規格",
        "summary": "長效 ARB (Telmisartan) 與 DHP 鈣通道阻斷劑 (Amlodipine) 複方。長效平穩控制 24 小時血壓。黑框警語：孕婦禁用。"
    },
    "olmesartan + amlodipine": {
        "starting_dose": "每日 1 錠 (常用規格 20/5 mg 或 40/5 mg 每日一次)",
        "max_daily_dose": "複方每日上限 1 錠 (最高規格 40/10 mg；Amlodipine 上限 10 mg/天、Olmesartan 上限 40 mg/天)",
        "timing": "每日一次固定時間服用，可隨餐或空腹",
        "titration": "給藥 2~4 週後依血壓監測滴定規格",
        "summary": "ARB (Olmesartan) 與 DHP 鈣通道阻斷劑 (Amlodipine) 複方降壓藥。黑框警語：孕婦禁用。"
    },
    "valsartan + hydrochlorothiazide": {
        "starting_dose": "每日 1 錠 (常用規格 80/12.5 mg 或 160/12.5 mg 每日一次)",
        "max_daily_dose": "複方每日上限 1 錠 (最高 320/25 mg；Valsartan 320 mg/天、HCTZ 25 mg/天)",
        "timing": "早晨固定時間服用，可隨餐或空腹 (避免夜尿)",
        "titration": "一般治療 2~4 週後評估降壓療效調整規格",
        "summary": "ARB (Valsartan) 併用利尿劑 (Hydrochlorothiazide) 複方降壓藥。黑框警語：孕婦禁用。注意低血鈉、低血鉀或高血鉀及尿酸變化。"
    },
    "losartan + hydrochlorothiazide": {
        "starting_dose": "每日 1 錠 (常用規格 50/12.5 mg 或 100/12.5 mg 每日一次)",
        "max_daily_dose": "複方每日上限 1 錠 (最高 100/25 mg；Losartan 100 mg/天、HCTZ 25 mg/天)",
        "timing": "早晨固定時間服用，可隨餐或空腹",
        "titration": "治療 2~4 週後評估血壓",
        "summary": "ARB (Losartan) 併用利尿劑 (Hydrochlorothiazide) 複方降壓藥。黑框警語：孕婦禁用。"
    },
    "empagliflozin + metformin": {
        "starting_dose": "依目前個別劑量 (如 5/500 mg 或 12.5/500 mg) 每日兩次隨餐服用",
        "max_daily_dose": "每日上限 25/2000 mg (Empagliflozin 25 mg / Metformin 2000 mg)",
        "timing": "早晚隨餐服用 (減少腸胃道不良反應)",
        "titration": "依血糖控制與耐受性遞增至常用維持劑量",
        "summary": "SGLT2 抑制劑 (Empagliflozin) 與 Metformin 複方。兼具心血管/腎臟保護與降糖效果。eGFR < 30 嚴格禁用 (乳酸中毒風險)。"
    },
    "linagliptin + metformin": {
        "starting_dose": "常用規格 2.5/500 mg 或 2.5/850 mg 每日兩次隨餐服用",
        "max_daily_dose": "每日上限 5/2000 mg (Linagliptin 5 mg / Metformin 2000 mg)",
        "timing": "早晚隨餐服用",
        "titration": "依血糖耐受性調整 Metformin 劑量",
        "summary": "DPP-4 抑制劑 (Linagliptin) 與 Metformin 複方。Linagliptin 不經腎臟排泄，但 Metformin 於 eGFR < 30 嚴格禁用。"
    },
    "amlodipine + atorvastatin": {
        "starting_dose": "每日 1 錠 (常用規格 5/10 mg 或 5/20 mg 每日一次)",
        "max_daily_dose": "每日上限 1 錠 (最高規格 10/80 mg；Amlodipine 10 mg/天、Atorvastatin 80 mg/天)",
        "timing": "每日固定時間服用一次 (早晚皆可)",
        "titration": "治療 4~8 週後追蹤血壓與 LDL-C 血脂調整劑量",
        "summary": "鈣離子阻斷劑 (Amlodipine) 與強效降血脂 Statin (Atorvastatin) 雙效複方。高血壓合併高膽固醇血症第一線整合治療。"
    },
    "amoxicillin + clavulanate": {
        "starting_dose": "成人常用 1,000 mg (含 Amox 875 mg + Clav 125 mg) 每 12 小時一次 (BID) 或 625 mg 每 8 小時一次 (TID)",
        "max_daily_dose": "每日最高 2,000 ~ 3,000 mg (以 Amoxicillin 計算)；Clavulanate 每日不宜超過 375~500 mg 以免重度腹瀉",
        "timing": "正餐前或用餐開始時服用 (減少腸胃道噁心與腹瀉，促進克拉維酸吸收)",
        "titration": "抗感染療程通常為 7~10 天，務必按時服畢",
        "summary": "廣效青黴素與 Beta-內醯胺酶抑制劑複方抗生素。盤尼西林過敏史者禁用。常見腹瀉、軟便不良反應。"
    },

    # ==================== 單方藥物 (Monotherapy) ====================
    # === 糖尿病 Antidiabetic ===
    "metformin": {
        "starting_dose": "500 mg 每日 1~2 次 (隨餐服用) 或 850 mg 每日一次",
        "max_daily_dose": "2,000 mg / 天 (ER 緩釋型)；2,550 mg / 天 (IR 速效型)",
        "timing": "隨餐或飯後立即服用 (以減少腸胃道噁心、腹瀉等不良反應)",
        "titration": "建議每 1~2 週依血糖監測與耐受性遞增 500 mg，分 2~3 次服用以達目標血糖",
        "summary": "第二型糖尿病第一線用藥。起始建議 500 mg 隨餐服用，耐受良好每週增加 500 mg 至常用維持劑量 1000~2000 mg/天。eGFR < 30 mL/min 嚴格禁用以防致死性乳酸中毒。"
    },
    "glimepiride": {
        "starting_dose": "1 mg ~ 2 mg 每日一次 (早餐前或當日第一餐前服用)",
        "max_daily_dose": "8 mg / 天 (多數臨床常用劑量為 1~4 mg / 天)",
        "timing": "早餐或第一餐正餐前立即服用 (促進餐後胰島素分泌)",
        "titration": "每 1~2 週視血糖監測依序遞增 1 mg 至 2 mg、4 mg",
        "summary": "第二代磺醯尿素類 (Sulfonylurea)。促胰島素分泌劑。主要副作用為低血糖及體重增加。年長者及腎功能不全者需減量並防低血糖。"
    },
    "gliclazide": {
        "starting_dose": "緩釋劑型 (MR) 30 mg 每日一次 (早餐前)",
        "max_daily_dose": "120 mg / 天 (MR 劑型)",
        "timing": "早餐前服用，整顆吞服勿壓碎",
        "titration": "每 2~4 週視血糖反應調整，每次遞增 30 mg",
        "summary": "磺醯尿素類促胰島素分泌劑。低血糖風險相對其他磺醯尿素類較低。腎功能不全者慎用。"
    },
    "sitagliptin": {
        "starting_dose": "100 mg 每日一次 (常規標準劑量)",
        "max_daily_dose": "100 mg / 天",
        "timing": "每日一次，可隨餐或空腹服用",
        "titration": "eGFR ≥ 45 免調整；eGFR 30~44 調至 50 mg QD；eGFR < 30 調至 25 mg QD",
        "summary": "DPP-4 抑制劑。藉由抑制腸泌素分解促進葡萄糖依賴性胰島素分泌。低血糖風險低，體重中性。需依 eGFR 進行腎功能階梯調整。"
    },
    "linagliptin": {
        "starting_dose": "5 mg 每日一次",
        "max_daily_dose": "5 mg / 天",
        "timing": "每日一次固定時間，可隨餐或空腹服用",
        "titration": "任何程度腎功能障礙或肝功能障礙皆無需調整劑量",
        "summary": "DPP-4 抑制劑。主要由膽汁與腸道排泄，各階段腎衰竭 (包括透析 ESRD) 均不需調整劑量，臨床腎病首選之一。"
    },
    "empagliflozin": {
        "starting_dose": "10 mg 每日一次 (早晨)",
        "max_daily_dose": "25 mg / 天",
        "timing": "早晨服用，可隨餐或空腹服用 (配合全天排鈉排水)",
        "titration": "耐受良好且需加強降糖控制者可於數週後增至 25 mg QD；心衰或 CKD 適應症以 10 mg QD 為主",
        "summary": "SGLT2 抑制劑。顯著降低心衰住院與腎病惡化風險。eGFR < 20 mL/min 不建議起始治療。需注意生殖泌尿道感染與正常血糖酮酸中毒 (eDKA)。"
    },
    "dapagliflozin": {
        "starting_dose": "10 mg 每日一次 (早晨)",
        "max_daily_dose": "10 mg / 天",
        "timing": "早晨固定時間服用，可隨餐或空腹",
        "titration": "標準建議固定劑量 10 mg QD",
        "summary": "SGLT2 抑制劑。證實具顯著心衰保護與腎臟保護益處。保持適當水分補充以預防低血壓及尿道感染。"
    },
    "pioglitazone": {
        "starting_dose": "15 mg ~ 30 mg 每日一次",
        "max_daily_dose": "45 mg / 天",
        "timing": "每日一次固定時間，可隨餐或空腹",
        "titration": "給藥數週後依血糖反應及水腫耐受性增量",
        "summary": "TZD 類胰島素增敏劑。黑框警語：可誘發或加重心衰竭 (NYHA III/IV 級禁用)。注意體重增加、周邊水腫及骨折風險。"
    },

    # === 心血管與降血壓 Cardiovascular & Antihypertensives ===
    "amlodipine": {
        "starting_dose": "常規起始 5 mg 每日一次；年長體弱或肝功能受損起始 2.5 mg 每日一次",
        "max_daily_dose": "10 mg / 天",
        "timing": "每日一次固定時間服用，可隨餐或空腹",
        "titration": "通常在給藥 7~14 天達穩定血中濃度後，視降壓療效與水腫耐受性調整至 10 mg",
        "summary": "長效型二氫吡啶 (DHP) 鈣離子通道阻斷劑。半衰期長 (35-50 小時)。常見不良反應為周邊水腫 (踝部水腫)、潮紅與頭痛。嚴重主動脈狹窄慎用。"
    },
    "bisoprolol": {
        "starting_dose": "高血壓/冠心症起始 2.5 ~ 5 mg 每日一次；心衰竭起始 1.25 mg 每日一次",
        "max_daily_dose": "20 mg / 天 (多數患者常規有效維持劑量為 5 ~ 10 mg / 天)",
        "timing": "早晨固定時間服用，可隨餐或空腹服用",
        "titration": "心衰竭患者每 2~4 週依耐受性倍增 (1.25 -> 2.5 -> 3.75 -> 5 -> 7.5 -> 10 mg QD)",
        "summary": "高選擇性 Beta-1 腎上腺素受體阻斷劑。降血壓、控制心絞痛與改善心衰竭長期存活率。需監測靜止心率 (HR < 50 bpm 應評估減量) 與血壓。嚴禁氣喘急性發作患者。"
    },
    "carvedilol": {
        "starting_dose": "高血壓起始 6.25 mg BID 或 12.5 mg QD；心衰竭起始 3.125 mg 每日兩次",
        "max_daily_dose": "高血壓 50 mg / 天；心衰竭體重 < 85kg 50 mg/天，> 85kg 100 mg/天",
        "timing": "隨餐服用 (食物可減緩吸收速率，降低姿勢性低血壓風險)",
        "titration": "心衰竭每 2 週依臨床症狀及耐受性倍增劑量至目標維持劑量",
        "summary": "非選擇性 Beta 阻斷兼具 Alpha-1 血管擴張作用。廣泛用於心衰竭與心肌梗塞後左心室功能不全。減緩心率兼具抗氧化效果。"
    },
    "losartan": {
        "starting_dose": "50 mg 每日一次 (使用利尿劑或血容積不足者由 25 mg 起始)",
        "max_daily_dose": "100 mg / 天 (可分一次或兩次服用)",
        "timing": "每日固定時間服用，可隨餐或空腹",
        "titration": "治療 3~6 週後評估降壓療效，若未達標可增至 100 mg QD",
        "summary": "血管收縮素受體阻斷劑 (ARB)。具降血壓與延緩糖尿病腎病變效益。孕婦嚴格禁用 (黑框胎兒毒性)。需監測血鉀與血清肌酸酐。"
    },
    "valsartan": {
        "starting_dose": "高血壓起始 80 mg ~ 160 mg 每日一次；心衰竭起始 40 mg 每日兩次",
        "max_daily_dose": "高血壓 320 mg / 天；心衰竭 160 mg BID (320 mg/天)",
        "timing": "每日固定時間服用，可隨餐或空腹",
        "titration": "心衰竭每 1~2 週倍增至目標劑量 160 mg BID",
        "summary": "ARB 類降血壓與心衰竭指引用藥。黑框警語：孕婦禁用 (胎兒毒性)。需監測高血鉀與腎功能變化。"
    },
    "telmisartan": {
        "starting_dose": "40 mg 每日一次 (部分患者 20 mg 即可達標)",
        "max_daily_dose": "80 mg / 天",
        "timing": "每日固定時間服用，可隨餐或空腹",
        "titration": "通常在治療 4~8 週後達最大降壓效果，必要時增至 80 mg QD",
        "summary": "超長半衰期 (24 小時) ARB 降血壓藥。具 PPAR-gamma 微弱激動活性。黑框警語：孕婦禁用。"
    },
    "isosorbide": {
        "starting_dose": "短效錠 (Mononitrate) 5~10 mg 每日兩次；長效緩釋劑型 (ER) 30~60 mg 每日一次",
        "max_daily_dose": "短效 40 mg / 天；長效緩釋 (ER) 120~240 mg / 天",
        "timing": "每日兩次劑型應相隔 7~8 小時 (如 08:00 與 15:00)，夜間維持 14 小時無硝酸鹽期間避免耐藥性",
        "titration": "由低劑量 5~10 mg 開始，第二至三天增至 20 mg BID；長效劑型早晨一次服用",
        "summary": "冠心症、狹心症預防與長期治療。非對稱性給藥 (相隔 7 小時) 以確保每日至少 12~14 小時低硝酸鹽濃度，避免產生血管耐受性。嚴禁與 PDE-5 抑制劑 (威而鋼、犀利士) 併用以防休克。"
    },
    "nitroglycerin": {
        "starting_dose": "舌下錠 (NTG) 0.3 ~ 0.6 mg 於胸痛發作時立即含於舌下",
        "max_daily_dose": "急性發作每 5 分鐘含 1 錠，15 分鐘內最多含 3 錠；若無緩解立即就醫",
        "timing": "心絞痛急性發作或預期勞力活動前 5~10 分鐘舌下含服",
        "titration": "不可吞服，坐姿含服以防姿勢性低血壓暈眩",
        "summary": "急性心絞痛急救首選。嚴禁與威而鋼等 PDE-5 抑制劑併用 (可能造成致命性低血壓休克)。"
    },
    "furosemide": {
        "starting_dose": "常規口服 20 mg ~ 40 mg 每日一次 (早晨)",
        "max_daily_dose": "口服可逐步調至 80~160 mg / 天 (重度水腫或腎衰竭可更高，分次給予)",
        "timing": "早晨服用 (若需每日兩次，第二劑應於下午 14:00 前服用以避免夜尿中斷睡眠)",
        "titration": "依體液過多症狀、每日尿量及體重變化動態微調",
        "summary": "亨利氏環利尿劑 (Loop Diuretic)。強效利尿脫水。需密切監測電解質 (低血鉀、低血鈉) 及腎功能 BUN/Cr。"
    },
    "spironolactone": {
        "starting_dose": "心衰竭起始 12.5 mg ~ 25 mg 每日一次；水腫/高血壓 25~50 mg 每日一次",
        "max_daily_dose": "心衰竭 50 mg / 天；肝硬化腹水可至 100~400 mg / 天",
        "timing": "早晨隨餐或飯後服用",
        "titration": "心衰竭給藥 4~8 週後可依血鉀 (需 < 5.0 mEq/L) 評估增至 50 mg QD",
        "summary": "保鉀利尿劑 / 醛固酮受體拮抗劑 (MRA)。顯著降低心衰竭死亡率。重度高血鉀風險，需規律追蹤鉀離子與腎功能。"
    },

    # === 降血脂 Lipid Lowering ===
    "atorvastatin": {
        "starting_dose": "常規起始 10 mg ~ 20 mg 每日一次；需大幅降 LDL-C > 45% 者起始 40 mg 每日一次",
        "max_daily_dose": "80 mg / 天",
        "timing": "每日一次固定時間服用 (早晚皆可，可隨餐或空腹，半衰期長約 14 小時)",
        "titration": "治療 4~12 週後抽血檢驗血脂，依心血管風險目標值調整劑量至 40~80 mg",
        "summary": "強效 HMG-CoA 還原酶抑制劑 (Statin)。顯著降低 LDL-C 及主要心血管事件。需監測肌肉痠痛 (橫紋肌溶解症罕見風險) 與肝功能 AST/ALT。"
    },
    "rosuvastatin": {
        "starting_dose": "常規起始 5 mg ~ 10 mg 每日一次；嚴重高膽固醇血症起始 20 mg 每日一次",
        "max_daily_dose": "40 mg / 天 (亞洲族群建議最高以 20 mg / 天為原則)",
        "timing": "每日一次固定時間，早晚皆可，可隨餐或空腹",
        "titration": "給藥 4 週後評估 LDL-C 達標率再行增量",
        "summary": "親水性超強效 Statin。顯著降 LDL 及升 HDL。亞洲族群血中濃度較高，一般建議由 5~10 mg 起始以維安全。"
    },
    "fenofibrate": {
        "starting_dose": "微粒化膠囊 (Micronised) 160 mg 或 200 mg 每日一次；奈米錠 145 mg 每日一次",
        "max_daily_dose": "160 mg / 天 (微粒化)；200 mg / 天 (標準型)",
        "timing": "隨餐服用 (食物可大幅促進微粒化劑型之胃腸道吸收與生體可用率)",
        "titration": "治療 4~8 週後評估三酸甘油酯 (TG) 及脂質濃度，若未達目標需重新評估",
        "summary": "高三酸甘油酯血症 (嚴重型 TG ≥ 500 mg/dL 可預防急性胰臟炎) 及混合型高血脂症。重度腎功能障礙 (eGFR < 30) 禁用。與 Statin 併用需嚴密防範肌病變。"
    },

    # === 抗血栓與抗凝血 Antithrombotic & Anticoagulant ===
    "warfarin": {
        "starting_dose": "通常 2.5 mg ~ 5 mg 每日一次 (依年齡、肝腎功能、營養狀態個體化評估)",
        "max_daily_dose": "無固定絕對上限，依定期監測之 PT/INR 凝血數值動態調整 (目標通常 2.0 ~ 3.0)",
        "timing": "每日固定於傍晚或睡前服用一次 (便於根據當日抽血報告調整處方)",
        "titration": "起始後第 2~3 天開始監測 INR，達標穩定前每 1~3 天檢驗，穩定後每 2~4 週監測一次",
        "summary": "口服抗凝血劑 (VKA)。治療窗狹窄，劑量完全依據 INR 調整。注意深綠色蔬菜等維生素 K 飲食變動及大量重大藥物交互作用。出血為主要嚴重風險。"
    },
    "aspirin": {
        "starting_dose": "心血管次級預防常規低劑量 100 mg 每日一次 (腸溶錠)",
        "max_daily_dose": "心血管抗血小板維持 100 mg / 天；急性冠心症起始負荷劑量 160~325 mg",
        "timing": "建議飯後服用，整顆吞服勿嚼碎 (保護胃腸道黏膜)",
        "titration": "常規維持 100 mg QD 長期服用",
        "summary": "不可逆 COX-1 抑制劑。心肌梗塞、缺血性中風次級預防基石。注意腸胃道潰瘍、胃出血及黑便徵兆。"
    },
    "clopidogrel": {
        "starting_dose": "維持劑量 75 mg 每日一次；急性冠心症 (ACS) 負荷劑量 300~600 mg 單次",
        "max_daily_dose": "75 mg / 天 (常規維持)",
        "timing": "每日一次固定時間，可隨餐或空腹服用",
        "titration": "支架術後雙抗血小板治療 (DAPT) 依臨床指引維持 6~12 個月",
        "summary": "P2Y12 受體拮抗劑。CYP2C19 慢代謝者抗血小板效果可能減弱。避免與強效 CYP2C19 抑制劑 Omeprazole 併用。"
    },

    # === 消化道與抑酸 Gastrointestinal & Acid ===
    "famotidine": {
        "starting_dose": "急性潰瘍 40 mg 每日一次 (睡前) 或 20 mg 每日兩次；GERD 20 mg BID",
        "max_daily_dose": "常規潰瘍 40~80 mg / 天；Zollinger-Ellison 重症高分泌可增至 160 mg 每 6 小時",
        "timing": "飯後或睡前 (HS) 服用 (夜間胃酸分泌高峰前達到最大抑酸保護)",
        "titration": "急性期治療 4~8 週，維持期可減半至 20 mg 睡前一次",
        "summary": "H2 受體拮抗劑。用於胃與十二指腸潰瘍、逆流性食道炎。中重度腎功能不全 (CrCl < 50 mL/min) 劑量應減半為 20 mg 睡前一次或每 36~48 小時給藥一次。"
    },
    "omeprazole": {
        "starting_dose": "20 mg 每日一次 (早餐前 30~60 分鐘)",
        "max_daily_dose": "40 mg / 天 (重度反流性食道炎或幽門螺旋桿菌除菌)",
        "timing": "早晨第一餐前 30 至 60 分鐘空腹服用 (達到最高質子泵抑制濃度)",
        "titration": "一般潰瘍治療 4~8 週；幽門螺旋桿菌除菌療程為 14 天",
        "summary": "質子泵抑制劑 (PPI)。強效抑酸。長期連續使用需監測骨質疏鬆骨折風險、維生素 B12 缺乏與低血鎂。"
    },
    "esomeprazole": {
        "starting_dose": "20 mg ~ 40 mg 每日一次 (早餐前 30~60 分鐘)",
        "max_daily_dose": "40 mg / 天 (嚴重 GERD 或 Zollinger-Ellison 症候群可至 80 mg/天)",
        "timing": "早餐前 30~60 分鐘空腹服用，膠囊整粒吞服",
        "titration": "糜爛性食道炎以 40 mg QD 治療 4~8 週，症狀緩解後以 20 mg QD 維持",
        "summary": "S-isomer 質子泵抑制劑。抑酸效果更持久。注意長期使用相關之艱難梭菌感染及鎂離子平衡。"
    },

    # === 抗生素 Antibiotics ===
    "levofloxacin": {
        "starting_dose": "500 mg 至 750 mg 每日一次 (依感染部位與適應症)",
        "max_daily_dose": "750 mg / 天",
        "timing": "每日一次固定時間，應避免與含鋁鎂制酸劑、鐵劑、鈣片同時服用 (需間隔至少 2 小時)",
        "titration": "依感染嚴重度治療 5~14 天。腎功能不全 (eGFR < 50) 必須依肌酸酐清除率延長給藥間隔或減量",
        "summary": "第三代 Fluoroquinolone 廣效抗生素。黑框警語：肌腱炎與肌腱斷裂、重症肌無力惡化、周邊神經病變、QT 波延長。eGFR < 50 需腎功能劑量校正。"
    },
    "amoxicillin": {
        "starting_dose": "500 mg 每 8 小時一次 (TID) 或 875 mg 每 12 小時一次 (BID)",
        "max_daily_dose": "2,000 mg ~ 3,000 mg / 天",
        "timing": "可隨餐或空腹服用 (隨餐可減少胃腸道不適)",
        "titration": "抗生素常規療程 7~10 天，務必按時服畢避免產生抗藥性",
        "summary": "廣效青黴素 (Penicillin)。盤尼西林過敏史者禁用。常見不良反應為腹瀉、皮疹及噁心。"
    },
    "cephalexin": {
        "starting_dose": "250 mg ~ 500 mg 每 6 小時一次 (QID) 或 500 mg 每 12 小時一次 (BID)",
        "max_daily_dose": "4,000 mg / 天",
        "timing": "可隨餐或空腹服用，多喝水",
        "titration": "常規療程 7~14 天，服至症狀緩解後至少 48 小時",
        "summary": "第一代口服頭孢菌素 (Cephalosporin)。革蘭氏陽性菌及呼吸道/軟組織感染。對頭孢菌素或嚴重盤尼西林過敏者禁用。"
    },

    # === 類固醇與消炎止痛 Steroids, NSAIDs & Analgesics ===
    "prednisolone": {
        "starting_dose": "生理維持 5~7.5 mg / 天；急性抗發炎 / 免疫抑制 15~60 mg / 天 (分次或單次晨服)",
        "max_daily_dose": "常規口服 60~80 mg / 天 (極重症免疫脈衝療法另計)",
        "timing": "早晨隨餐或飯後服用 (配合人體下視丘-腦下垂體生理節律，減低胃刺激與失眠)",
        "titration": "病情控制後應漸進緩慢減量 (Tapering)，避免發生急性腎上腺皮質機能不全",
        "summary": "中效口服糖皮質素類固醇。抗發炎及免疫抑制。長期使用需監測血壓、血糖、骨質密度、電解質及感染徵兆。不可無預警突然停藥。"
    },
    "acetaminophen": {
        "starting_dose": "500 mg 單次 1~2 錠，每 4~6 小時一次，必要時服用 (PRN)",
        "max_daily_dose": "4,000 mg / 天 (一般成人)；年長體弱、慢性肝病或飲酒者上限 2,000~2,600 mg / 天",
        "timing": "疼痛或發燒時服用，飯前飯後皆可，避免與酒精併服",
        "titration": "單次不超過 1000 mg，兩次間隔至少 4 小時",
        "summary": "第一線解熱鎮痛藥。黑框警語：過量具嚴重急性肝衰竭毒性。務必檢視所有併用複方感冒藥，避免乙醯胺酚成分重複累積超量。"
    },
    "celecoxib": {
        "starting_dose": "骨關節炎 200 mg 每日一次 (或 100 mg BID)；類風濕性關節炎 100~200 mg BID",
        "max_daily_dose": "400 mg / 天",
        "timing": "可隨餐或空腹服用 (隨餐高脂飲食可能延緩吸收但減輕胃部不適)",
        "titration": "應使用能控制症狀之最低有效劑量與最短療程",
        "summary": "選擇性 COX-2 抑制劑。胃腸道潰瘍風險較傳統 NSAID 低。黑框警語：增加重大心血管血栓事件 (心肌梗塞/中風) 風險。對磺胺藥 (Sulfonamide) 過敏者禁用。"
    },

    # === 腎臟與透析電解質 Nephrology & ESRD ===
    "calcium acetate": {
        "starting_dose": "667 mg (1 錠) 至 1,334 mg (2 錠) 隨三餐服用",
        "max_daily_dose": "每餐最多 3~4 錠 (每日上限約 8,000 mg / 12 錠，需依血清鈣磷濃度調整)",
        "timing": "隨餐立即吞服或嚼碎 (與食物中的磷酸鹽充分混合結合排出)",
        "titration": "每 2~3 週依血清磷濃度調整，目標維持血清磷 3.5 ~ 5.5 mg/dL，監測血鈣避免高血鈣",
        "summary": "末期腎病 (ESRD) 與透析患者之高磷血症磷結合劑。必須隨餐服用方具結合飲食中磷酸鹽之療效。定期監測鈣磷乘積 (Ca x P < 55) 與血清鈣濃度。"
    },
    "calcium": {
        "starting_dose": "鈣結合劑 667 mg ~ 1,334 mg 隨餐服用；鈣質補充 500 mg ~ 600 mg 每日 1~2 次",
        "max_daily_dose": "元素鈣每日總上限約 2,000 mg (含飲食)",
        "timing": "磷結合劑必須隨餐服用；骨質補充劑建議飯後服用以助吸收",
        "titration": "依血清鈣濃度及 PTH 指標定期調整",
        "summary": "含鈣製劑 (碳酸鈣/醋酸鈣)。腎衰竭患者注意高血鈣及血管鈣化風險。避免與鐵劑、抗生素同時間服用。"
    },

    # === 呼吸與過敏 Allergy & Respiratory ===
    "mequitazine": {
        "starting_dose": "5 mg 每日兩次 (早晚各 1 錠) 或 10 mg 睡前一次",
        "max_daily_dose": "10 mg / 天",
        "timing": "早晚飯後或睡前服用",
        "titration": "症狀緩解後可評估停藥或按需服用",
        "summary": "長效抗組織胺。用於過敏性鼻炎、蕁麻疹及皮膚搔癢。具輕微嗜睡及抗膽鹼作用，青光眼及攝護腺肥大者慎用。"
    },
    "cetirizine": {
        "starting_dose": "10 mg 每日一次 (或 5 mg 每日兩次)",
        "max_daily_dose": "10 mg / 天",
        "timing": "傍晚或睡前服用 (部分患者具輕度嗜睡)",
        "titration": "腎功能不全者 (CrCl 11~31) 建議減半為 5 mg 每日一次",
        "summary": "第二代抗組織胺。迅速緩解過敏性鼻炎與急性蕁麻疹。駕駛或操作機械需注意嗜睡反應。"
    },

    # === 皮膚科外用藥 Topical ===
    "heparinoid": {
        "starting_dose": "適量凝膠或乳膏塗抹於患部，每日 2 ~ 3 次，輕輕按摩至吸收",
        "max_daily_dose": "依患部面積薄塗，避免大面積破損皮膚濫用",
        "timing": "清潔皮膚後塗抹",
        "titration": "持續使用數天至數週直至血腫或靜脈炎瘀血消退",
        "summary": "外用類肝素凝膠/乳膏。具抗血栓、促進局部血液循環與組織修復消腫作用。嚴禁塗抹於開放性傷口、黏膜或潰爛感染皮膚。"
    },
    "fusidic acid": {
        "starting_dose": "薄塗於患部，每日 2 ~ 3 次，療程通常 7 ~ 14 天",
        "max_daily_dose": "局部外用，避免過度長期廣泛塗抹",
        "timing": "清潔患部後塗抹，必要時可加蓋紗布",
        "titration": "連續使用一般不宜超過 14 天以避免細菌耐藥性",
        "summary": "外用抗生素 (褐黴素軟膏/乳膏)。對金黃色葡萄球菌具強效殺菌。主要用於膿痂疹、毛囊炎與淺表皮膚細菌感染。"
    },
    "naftifine": {
        "starting_dose": "每日一次，薄塗於洗淨乾燥之患部及其周圍健康皮膚約 1 公分範圍",
        "max_daily_dose": "局部外用每日 1 次",
        "timing": "建議傍晚或洗澡後擦乾皮膚塗抹",
        "titration": "臨床症狀消失後，應持續使用至少 1~2 週以防真菌復發",
        "summary": "Allylamine 類抗黴菌外用藥。用於足癬 (香港腳)、股癬、體癬。避免接觸眼睛與黏膜部位。"
    }
}



__all__ = [
    "MOIETY_CHINESE_NAMES",
    "MOIETY_DRUG_CLASSES",
    "MOIETY_MONOTHERAPY_DOSES",
    "MOIETY_CLINICAL_REMARKS",
    "FALLBACK_LIMITS",
    "CLINICAL_DOSING_KB",
]
