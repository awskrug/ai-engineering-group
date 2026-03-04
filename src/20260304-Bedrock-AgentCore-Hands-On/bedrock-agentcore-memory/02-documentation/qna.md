## General QnA

### 1. RAG와 Episodic Memory의 가장 큰 차이점은 무엇인가요?

RAG는 과거 데이터를 chunk 단위로 나누어 벡터 DB에 저장하고, 질문이 들어오면 관련 chunk를 검색하여 컨텍스트로 제공하는 방식입니다. 즉, 과거 정보를 검색 기반으로 다시 불러오는 구조입니다.

반면 Episodic Memory는 대화 turn들을 의미 단위로 묶어 하나의 Episode로 구조화합니다. 이후 여러 Episode가 축적되면 이를 통합하여 Reflection이라는 인사이트 단위를 생성합니다.

정리하면, RAG는 검색 중심 구조이고, Episodic Memory는 구조화와 추상화를 기반으로 장기적인 경험을 축적하는 구조입니다. 단순한 정보 재사용이 아니라, 과거 경험을 해석하고 재구성하는 방식이라는 점이 가장 큰 차이입니다.

### 2. 왜 Reflection은 Session 레벨에 저장할 수 없나요?
Reflection은 단일 세션에서 생성되는 정보가 아니라, 여러 Episode를 통합하여 도출된 장기적 인사이트입니다. 예를 들어, 특정 사용자의 반복적인 학습 패턴이나 행동 습관은 여러 세션에 걸쳐 축적된 결과입니다.

Session 레벨에 저장하면 해당 세션 범위 내에서만 활용 가능하게 되므로, 장기적인 패턴 분석이라는 Reflection의 목적과 맞지 않습니다. 따라서 Reflection은 세션을 초월해 활용될 수 있도록 Actor 레벨 또는 Strategy 레벨에 저장됩니다.

### 3. Reflection이 잘못된 인사이트를 생성할 가능성은 없나요?
가능성이 있습니다. Reflection은 LLM 기반의 통합 및 추상화 과정을 통해 생성되기 때문에, 입력 데이터의 분포나 맥락에 따라 과도한 일반화나 편향이 발생할 수 있습니다.

이를 완화하기 위해서는 다음과 같은 설계가 필요할 수 있습니다.
- Custom Prompt를 통해 일반화 기준과 통합 조건(Consolidation)을 명확히 정의
- Reflection 생성 이후 Inspect 또는 검증 단계를 통해 결과를 확인

이와 같은 방식으로 Reflection의 품질을 관리할 수 있습니다.

### 4. 모든 use case에 Episodic Strategy가 적합한가요?
아닙니다. Episodic Strategy는 행동 패턴, 문제 해결 과정, 장기 학습 추적 등과 같이 시간에 따른 변화와 맥락 축적이 중요한 use case에 적합합니다.

반면, 단순한 사실 정보 저장이나 변하지 않는 정적 정보 관리에는 Semantic 전략이 더 적합할 수 있습니다. 세션 단위 요약이 목적이라면 Summary 전략이 더 효율적일 수 있습니다.
따라서 전략 선택은 저장하려는 정보의 성격과 시스템의 목적에 따라 결정해야 합니다.

### 5. Actor 레벨과 Session 레벨은 어떻게 결정하나요?
Namespace 레벨 선택은 저장하려는 정보의 범위를 기준으로 결정합니다.
Actor 레벨은 사용자 단위로 장기적인 메모리를 축적하고자 할 때 적합합니다. 여러 세션에 걸친 학습 기록이나 행동 패턴을 유지하려는 경우에 사용됩니다.

Session 레벨은 특정 세션 내에서만 유효한 정보를 분리하여 관리하고자 할 때 적합합니다. 예를 들어, 일회성 작업이나 독립된 실험 환경에 활용할 수 있습니다.

### 6. 비용 측면에서 RAG보다 더 비싸지 않나요?
Episodic Memory는 Episode 생성과 Reflection 통합 과정에서 LLM 기반 평가를 수행하기 때문에, 초기 구조화 단계에서 추가 비용이 발생할 수 있습니다.

그러나 Retrieval 단계에서는 구조화된 의미 단위를 검색하기 때문에, 불필요한 chunk를 다수 가져오는 RAG 방식에 비해 컨텍스트 토큰 사용량을 줄일 수 있습니다. 이로 인해 응답 생성 단계에서는 토큰 비용을 절감할 가능성이 있습니다.

따라서 단기적으로는 구조화 비용이 존재하지만, 장기적으로는 효율적인 검색과 컨텍스트 최적화를 통해 비용 균형을 맞출 수 있습니다.

### 7. Episode와 Reflection의 구조가 어떻게 되나요?
Built-in 방식으로 생성되는 Episode와 Reflection의 System Prompt 을 참고해주시기 바라며, 해당 내용은 
System prompts for episodic memory strategy에 대한 [공식문서](https://docs.aws.amazon.com/ko_kr/bedrock-agentcore/latest/devguide/memory-episodic-prompt.html) 을 통해 참고하실 수 있습니다.

