# TikTok Shop Seller API 신청 가이드

> 이 가이드는 TikTok Shop API를 통해 주문, 상품, 캠페인 데이터를 자동으로 수집하기 위한 API 신청 절차를 안내합니다.

---

## 목차

1. [사전 준비사항](#1-사전-준비사항)
2. [Partner Center 등록](#2-partner-center-등록)
3. [앱 생성](#3-앱-생성)
4. [API 자격증명 획득](#4-api-자격증명-획득)
5. [API 권한 신청](#5-api-권한-신청)
6. [개발팀 전달 정보](#6-개발팀-전달-정보)
7. [예상 소요 시간](#7-예상-소요-시간)
8. [참고 자료](#8-참고-자료)

---

## 1. 사전 준비사항

API 신청 전 다음 항목을 준비해 주세요:

| 항목 | 설명 |
|------|------|
| TikTok Shop Seller Center 계정 | 활성화된 셀러 계정 필요 |
| 사업자 등록증 | 법인 또는 개인사업자 |
| 담당자 신분증 | 여권 또는 주민등록증 |
| 개인정보처리방침 URL | 웹사이트에 게시된 개인정보처리방침 |

---

## 2. Partner Center 등록

### 2-1. Partner Portal 접속

| 대상 마켓 | URL |
|----------|-----|
| **글로벌 (인도네시아 포함)** | https://partner.tiktokshop.com |
| 미국 전용 | https://partner.us.tiktokshop.com |

> **인도네시아 마켓 대상이면 Global Partner Portal을 선택하세요.**

### 2-2. 등록 절차

1. **"Get Started"** 버튼 클릭

2. **Business Region 선택**
   - 사업체가 등록된 국가 선택
   - ⚠️ **주의: 한 번 설정하면 변경 불가능합니다!**

3. **Target Market 선택**
   - `Indonesia` 선택

4. **Business Category 선택**
   - `Seller in-house developer` 선택
   - (자사 스토어 데이터 연동 목적)

5. **이메일 인증**
   - TikTok Shop 관리자 이메일로 인증 코드 수신
   - 인증 코드 입력하여 본인 확인

6. **서류 제출**
   - 사업자 등록증 업로드
   - 담당자 신분증 업로드

7. **제출 및 승인 대기**
   - 약 **2-3 영업일** 소요

---

## 3. 앱 생성

### 3-1. 앱 생성 메뉴 접속

1. Partner Center 로그인
2. 좌측 메뉴에서 **"App & Service"** 클릭
3. **"Create app & service"** 버튼 클릭

### 3-2. 앱 유형 선택

| 유형 | 설명 | 권장 |
|------|------|------|
| **Custom App** | 자사 스토어 전용 앱 | ✅ **권장** |
| Public App | TikTok Shop 앱스토어에 공개 | - |

> Custom App을 선택하세요. 자사 데이터 연동 목적에 적합합니다.

### 3-3. 앱 정보 입력

| 항목 | 입력 예시 |
|------|----------|
| **App Name** | `[브랜드명] Data Integration` |
| **Category** | `E-commerce` 또는 `Analytics` |
| **Logo** | 브랜드 로고 이미지 (PNG, 512x512px 권장) |
| **Target Market** | `Indonesia` |
| **Redirect URL** | 개발팀에서 제공 (예: `https://your-domain.com/callback`) |
| **Webhook URL** | 개발팀에서 제공 (선택사항) |

### 3-4. 앱 생성 완료

**"Submit"** 버튼을 클릭하면 앱이 즉시 생성됩니다.

---

## 4. API 자격증명 획득

앱 생성이 완료되면 앱 상세 페이지에서 다음 정보를 확인할 수 있습니다:

```
┌────────────────────────────────────────────────────┐
│                                                    │
│   App Key:      7abc1234567890def1234567890abc     │
│                                                    │
│   App Secret:   9xyz9876543210fed0987654321xyz     │
│                                                    │
│   Service ID:   1234567                            │
│                                                    │
└────────────────────────────────────────────────────┘
```

### 보안 주의사항

| 항목 | 공개 가능 | 비고 |
|------|----------|------|
| App Key | O | 클라이언트 식별용 |
| **App Secret** | **X** | **절대 외부 노출 금지** |
| Service ID | O | 서비스 식별용 |

> **App Secret이 노출되면 즉시 재발급 받아야 합니다.**

---

## 5. API 권한 신청

### 5-1. 권한 신청 메뉴 접속

1. 앱 상세 페이지에서 **"Manage API"** 클릭
2. 필요한 권한 목록 확인

### 5-2. 필요 권한 목록

| 권한 (Scope) | 용도 | 필요 여부 |
|-------------|------|----------|
| `order.read` | 주문 데이터 조회 | ✅ **필수** |
| `product.read` | 상품 데이터 조회 | ✅ **필수** |
| `analytics.read` | 분석/캠페인 데이터 조회 | ✅ **필수** |
| `finance.read` | 정산 데이터 조회 | 선택 |
| `logistics.read` | 배송/물류 데이터 조회 | 선택 |
| `shop.read` | 스토어 정보 조회 | 선택 |

### 5-3. 권한 신청 방법

1. 각 권한 옆의 **"Apply"** 버튼 클릭
2. **사용 목적** 작성 (영문)

   예시:
   ```
   We need this permission to sync order data with our
   internal analytics dashboard for sales performance
   monitoring and inventory management.
   ```

3. **"Submit"** 클릭
4. **승인 대기**: 약 1-5 영업일

---

## 6. 개발팀 전달 정보

API 승인이 완료되면 아래 정보를 개발팀에 전달해 주세요:

### 전달 정보 체크리스트

```
[ ] App Key: ________________________________________

[ ] App Secret: ________________________________________

[ ] Service ID: ________________________________________

[ ] Shop ID: ________________________________________
    (Seller Center > Settings > Shop Information에서 확인)

[ ] 승인된 권한 목록:
    [ ] order.read
    [ ] product.read
    [ ] analytics.read
    [ ] finance.read
    [ ] logistics.read
    [ ] 기타: ______________
```

### Shop ID 확인 방법

1. TikTok Shop Seller Center 로그인
2. 우측 상단 **Settings(설정)** 클릭
3. **Shop Information(스토어 정보)** 메뉴
4. **Shop ID** 복사

---

## 7. 예상 소요 시간

| 단계 | 소요 시간 |
|------|----------|
| Partner Center 등록 승인 | 2-3 영업일 |
| 앱 생성 | 즉시 |
| API 권한 승인 | 1-5 영업일 |
| OAuth 인증 설정 | 1-2 영업일 (개발팀) |
| **총 예상 소요 시간** | **약 1-2주** |

---

## 8. 참고 자료

### 공식 문서

- [TikTok Shop Partner Center](https://partner.tiktokshop.com)
- [개발자 가이드](https://partner.tiktokshop.com/docv2/page/tts-developer-guide)
- [Seller API Overview](https://partner.tiktokshop.com/docv2/page/seller-api-overview)
- [TikTok for Developers](https://developers.tiktok.com/)

### 추가 참고

- [TikTok Shop API Integration Guide (KeyAPI)](https://www.keyapi.ai/blog/tiktok-shop-api-integration-guide-sellers)
- [TikTok Business API Portal](https://business-api.tiktok.com/portal)

---

## 문의

API 신청 과정에서 문의사항이 있으시면 연락 주세요.

- 담당자: _______________
- 이메일: _______________
- 전화: _______________

---

*마지막 업데이트: 2026년 4월*
