# Chrome 디버그 모드 실행 가이드

## 🚀 바이럴 감지 시스템 실행 준비

# Chrome 디버그 모드 실행 가이드

## 🚀 바이럴 감지 시스템 실행 준비

### ⚠️ 중요: 기존 Chrome 프로필 유지하면서 디버그 모드 실행

**방법 1: 기존 프로필 사용 (권장)**
```bash
# 1. 기존 Chrome 완전 종료 (Cmd+Q)
# 2. 기존 프로필로 디버그 모드 실행
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

**방법 2: 별도 Chrome 인스턴스 실행 (북마크 유지)**
```bash
# 기존 Chrome은 그대로 두고, 새 창에서 디버그 모드 실행
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --new-window
```

**방법 3: 기존 Chrome이 실행 중일 때**
```bash
# Chrome 설정에서 "원격 디버깅" 활성화
# chrome://flags/#enable-remote-debugging 에서 활성화 후 재시작
```

### 🔧 현재 상황 해결 방법

**1단계: 임시 Chrome 종료**
- Chrome을 완전히 종료하세요 (Cmd+Q)

**2단계: 정상 Chrome으로 복구**
```bash
# 정상적인 Chrome 실행 (북마크/로그인 정보 복구됨)
open -a "Google Chrome"
```

**3단계: 바이럴 감지 시스템 사용 시에만 디버그 모드**
```bash
# 필요할 때만 디버그 모드로 실행
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

### 2단계: 연결 테스트
```bash
python3 test_viral_detector.py
```

### 3단계: 바이럴 감지 시스템 실행
```bash
python3 viral_detector.py
```

## ⚠️ 주의사항

1. **Chrome 완전 종료 필요**: 기존 Chrome 창이 열려있으면 디버그 모드로 실행되지 않습니다.
2. **포트 9222 사용**: 다른 프로그램이 9222 포트를 사용 중이면 실패할 수 있습니다.
3. **방화벽 설정**: macOS 방화벽에서 Chrome 접근을 허용해야 할 수 있습니다.

## 🔧 문제 해결

### Chrome이 실행되지 않는 경우
```bash
# Chrome 프로세스 확인
ps aux | grep Chrome

# Chrome 프로세스 강제 종료
pkill -f Chrome
```

### 포트 충돌 확인
```bash
# 9222 포트 사용 확인
lsof -i :9222

# 다른 포트 사용 (9223)
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9223
```

## 📊 실행 후 확인사항

Chrome 디버그 모드가 성공적으로 실행되면:
- 새 Chrome 창이 열림
- 주소창에 "Chrome is being controlled by automated test software" 메시지 표시
- 터미널에 디버그 정보 출력

이제 바이럴 감지 시스템을 실행할 준비가 완료되었습니다!

## 📱 사용자 친화적 해결책

### 옵션 A: 데모 버전 사용 (Chrome 불필요)
```bash
# 실제 크롤링 없이 시뮬레이션 데이터로 테스트
python3 viral_detector_demo.py
```

### 옵션 B: 기존 Chrome 유지하면서 테스트
1. 현재 Chrome을 그대로 사용하세요 (북마크/로그인 정보 유지)
2. 바이럴 감지 시스템이 필요할 때만 잠시 디버그 모드로 전환
3. 테스트 완료 후 정상 Chrome으로 복구

### 옵션 C: 별도 브라우저 사용
- Safari나 Firefox로 일반 브라우징
- Chrome은 바이럴 감지 전용으로 사용

## 🚨 긴급 복구 방법

**지금 당장 정상 Chrome으로 돌아가려면:**

1. **Chrome 완전 종료**
   ```bash
   # 터미널에서 실행
   pkill -f Chrome
   ```

2. **정상 Chrome 실행**
   ```bash
   open -a "Google Chrome"
   ```

3. **북마크/로그인 정보 확인**
   - 모든 북마크와 로그인 정보가 복구됩니다
   - 확장 프로그램도 정상 작동합니다

## 💡 앞으로의 권장 사용법

1. **일반 사용**: 평소처럼 Chrome 사용
2. **바이럴 감지 필요시**: 
   - Chrome 종료 → 디버그 모드 실행 → 바이럴 감지 → Chrome 정상 실행
3. **또는 데모 버전 사용**: 실제 크롤링 없이 시뮬레이션으로 테스트