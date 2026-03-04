## Troubleshootings & Findings
1. Session Data Batch Ingestion에 소요되는 시간 단축하기
2. Retriever Customize에 대한 생각 
3. Logging 활성화(Add Log delivery)
4. Prompt Override의 필요성

### 1. Session Data Batch Ingestion에 소요되는 시간 단축하기
궁금증 :
- 과거 세션 데이터를 Ingestion하고 난 후에 어떤 조건에 의해 Memory Extraction Module이 Trigger되는것일까?
- Ingestion 이후 Memory Extraction Process가 완료되기까지 일반적으로 18~20분이 소요되며, 그 중 15분은 Idle Time인것으로 보이며, 실제 Processing Time은 대략 3분
- 15분을 대기하지 않고 바로 Processing을 시작할 수 없을지, 어떤 조건을 만족할 경우 15분의 Idle Time을 기다리지 않도록 할 수 있을까?

발견 :
- Turn을 수집하였을때 `AssessmentUser` 필드는 대화 세션에서 User의 Goal이 Achieved 되었는지를 평가한다.
    ```
    {'situation': '학생이 천천히 하니 실수하지 않는다는 것을 체험함',
    'intent': '1주차 수업 정리를 위해 핵심 개념 확인',
    'action': '1주차 수업 정리를 제안하며 세로셈 곱셈에서 가장 중요한 것 질문',
    'thought': '수업 마무리 단계에서 핵심 개념을 정리하여 학습 내용 고착화',
    'assessmentAssistant': 'Yes - 수업 정리 단계로 전환하여 핵심 개념 확인',
    'assessmentUser': 'No - 학생이 핵심 개념을 정확히 답변'}
    ```
- 이때 YES라고 평가되었다면 에피소드가 종료된 것으로 인식하고 Episode Generation Process을 시작한다. 즉, Memory Extraction Module을 진행한다. 하지만, NO으로 판단될 경우 15분의 Idle Time을 가지며, 이후에 Memory Extraction Module이 Trigger 된다.
- 즉, Idle Time(15분의 대기시간)을 단축하기 위해서는 세션 구성에서 `Goal Achieved?` 에 `YES`라고 LLM이 판단해야 하는것..

### 2. Retriever Customize에 대한 생각 
문제점 :
- 현재 방식은 `AgentcoreMemorySesionManager`을 생성하여 Agent에게 전달하는 방식을 통해 Agent와 Memory을 연동한다.
- 하지만 이 방식을 사용하면 실제 Retrieve한 메모리가 무엇이었는지 뜯어보거나 내부 프로세스를 제어하기 어려움.
- 예를들어, 
    - 특정 상황에서는 Reflection이 아니라 Episode에 대한 Records만을 참조하도록 하고 싶다면?(예: 2주차 분수 곱셈문제를 다시 내줘) 
    - 혹은 반대로 Episode가 아닌 Reflection만을 참고하도록 하고 싶을 수 있다.(예: 문제풀이 성향 분석 결과 알려줘)
    - 혹은 Memory Inspection의 절차를 부여하고 싶다면?(예: Episode을 먼저 탐색하고 그 결과에 따라 Reflection 탐색)

시도한 내용 :
- `AgentcoreMemorySesionManager`을 사용하여 Agent와 Memory을 구성하는 방식을 사용하지 않고, Memory Retriever을 Tool으로서 구성하고, 각각의 시나리오에 맞는 Tool을 연결한다.
- 예를들어, [공식 노트북 예제](https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/04-AgentCore-memory/02-long-term-memory/01-single-agent/using-strands-agent-memory-tool/debugging-agent/debugging_assistant_episodic_memory.ipynb) 을 참고하면, 아래와 같이 Reflection Memory Retriever와 Episode Memory Retriever을 별도로 만들어 Tool으로서 Agent와 연결하였음
    <details>
    <summary>코드 참고</summary>

    ```python
    # Create memory retrieval tools for the agent

    @tool
    def retrieve_process(task: str, include_steps: bool = True) -> str:
        """
        Retrieve example processes to help solve the given task. Returns complete debugging
        episodes with configurable detail level.
        
        Use include_steps parameter to control verbosity:
        - Set include_steps=True when user asks for "exact steps", "full details", "how did we",
        "what steps did we take", or needs complete procedural information
        - Set include_steps=False for pattern/best practice queries where high-level context
        (situation, intent, assessment) is sufficient without step-by-step details

        Args:
            task: The task to solve that requires example processes
            include_steps: Whether to include detailed step-by-step turns (default: True)

        Returns:
            Formatted debugging episodes with optional detailed steps
        """
        logger.info(f"🔍 Retrieving processes for task: {task} (include_steps={include_steps})")
        
        try:
            # Search in episode namespace
            namespace = f"debugging/{ACTOR_ID}/sessions/{session_id}/"
            
            # Use boto3 client directly to retrieve memory records
            response = client.retrieve_memory_records(
                memoryId=memory_id,
                namespace=namespace,
                searchCriteria={
                    'searchQuery': task,
                    'topK': 3
                },
                maxResults=20
            )
            
            episodes = response.get('memoryRecordSummaries', [])
            logger.info(f"   Found {len(episodes)} relevant episodes")
            
            # Linearize with configurable detail level
            return linearize_episodes(episodes, include_steps=include_steps, include_reflections=True)
            
        except Exception as e:
            logger.error(f"Error retrieving processes: {e}")
            return f"Error retrieving processes: {str(e)}"
            


    @tool
    def retrieve_reflection_knowledge(task: str, k: int = 5) -> str:
        """
        Retrieve synthesized reflection knowledge from past agent experiences. Each knowledge 
        entry contains: (1) a descriptive title, (2) specific use cases for when to apply it, 
        and (3) actionable hints including best practices from successful episodes and common 
        pitfalls to avoid from failed episodes. Use this to get strategic guidance and patterns
        for similar tasks.

        Args:
            task: The current task to get strategic guidance for
            k: Number of reflection entries to retrieve (default: 5)

        Returns:
            Synthesized reflection knowledge from past debugging experiences
        """
        logger.info(f"🔍 Retrieving reflection knowledge for task: {task}")
        
        try:
            # Search in reflection namespace
            namespace = f"debugging/{ACTOR_ID}/"
            
            # Use boto3 client directly to retrieve memory records
            response = client.retrieve_memory_records(
                memoryId=memory_id,
                namespace=namespace,
                searchCriteria={
                    'searchQuery': "memory leaks",
                    "metadataFilters":[{"left":{"metadataKey": "x-amz-agentcore-memory-recordType"},
                                        "operator": "EQUALS_TO",
                                        "right": {"metadataValue": {"stringValue": "REFLECTION"}}
                                        }],          
                    'topK': k
                },
                maxResults=20
            )
            
            reflections = response.get('memoryRecordSummaries', [])
            logger.info(f"   Found {len(reflections)} relevant reflection insights")
            
            # Linearize reflections
            return linearize_reflections(reflections)
            
        except Exception as e:
            logger.error(f"Error retrieving reflections: {e}")
            return f"Error retrieving reflections: {str(e)}"


    logger.info("✅ Memory retrieval tools created")
    ```
    </details>

기대 효과 : 
- Retrieve 과정을 세밀하게 조정할 수 있다.
- 시나리오에 따라 Retrieve 하는 Namespace을 다르게 설정할 수 있다.
- 일반적인 Tool 호출 방식과 동일하게 개발할 수 있다.

### 3. Logging 활성화(Add Log delivery)
문제점 : 
- 기본적으로 Agentcore Memory을 생성할때 Logging 설정이 별도로 Enable 되어있지 않다.
- 1번 문제에서와 같이 Memory Extraction Module의 Process을 트래킹 해야하는 상황에서 로그를 활용하기 어려움.

해결 방안 : 
- Memory 리소스 생성시점에 Log Delivery을 Add하도록 하자!
- 콘솔에서 Add Log Delivery을 통해 추가하면 가장 간단하게 설정할 수 있으며, 코드로서 작업하기 위해서는 아직 별도의 API는 없는것으로 확인된다. 따라서 hands-on lab에서와 같이 Cloudwatch API을 이용하여 셀을 구성하였다. 

### 4. Prompt Override의 필요성 (Customize a built-in strategy)
문제점 : 
- Built-in Prompt을 사용하였을때 Episode 추출 결과 불필요한 정보들을 중요하게 판단하여 에피소드를 구성하고 수집하는 경향을 보임
- 예 : “학생이 선생님에게 감사를 어떻게 표시하였다”와 같이 학생의 문제 해결 과정과 관련 없는 내용들을 에피소드로 추출
- 예 : "1+1 = 2" 문제를 어떤 접근으로 풀다가 틀렸는지 과정을 추출하는것이 아니라, "덧셈 문제를 틀려서 학생이 우울해함" 와 같이 Usecase와 맞지 않는 정보를 추출
- 일반적인 상황에서는 대부분 잘 추출하지만, 위와같은 사례가 간헐적으로 발생하며, 이는 내가 테스트하고자 하는 시나리오에 맞지 않았음

시도한 내용 : 
- `EXTRACTION_PROMPT` 을 Override해서 “문제 해결과정”을 위주로 에피소드를 추출하도록 지시 
- 단, [문서](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-custom-strategy.html)에 따르면 Episode나 Consolidation, Reflection의 Output format을 변경할 수 없으므로 기존의 포맷을 유지해야 한다. 예를들면 Episode는 `situation`, `intent`, `assessment`, 등 ... 의 Output 구조를 유지한다.
    > Output schema is not editable: built-in with overrides strategies do not let you change the final output schema of the extracted or consolidated memory. The output schema that will be added to the system prompt for the built-in with overrides strategy will be same as the built-in strategies.
    
- `EXTRACTION_PROMPT` 변경사항 : 
    ```
    ...
    For <action>:
    - Include the specific problem and student's answer
    - Describe what happened: problem → student's solving steps → answer (correct/incorrect)
    - Example: "23×4 문제 → 3×4=12, 2×4=8로 계산 → 82 답함 (오답, 정답: 92)"
    For <thought>:
    - Why the error occurred (underlying misconception)
    - Teaching method used and why
    - Any patterns observed in student's behavior
    ```


결과 :
- 아래 예시를 살펴보면, 실제 문제 해결과정이 잘 드러나도록 추출된 점이 확인됨. 
- Prompt에서 지시한대로 `action`, `thought`에 해당하는 부분에 내용이 수집됨
    ```
    {'situation': "학생이 '올림'이라는 새로운 개념에 대해 질문",
    'intent': '올림 개념을 3×4=12 예시로 구체적으로 설명',
    'action': '3×4=12에서 십의 자리 1과 일의 자리 2로 분해하여 올림 개념 설명',
    'thought': '추상적인 올림 개념을 구체적인 숫자 분해로 이해하기 쉽게 설명 필요',
    'assessmentAssistant': 'Yes - 구체적인 예시로 올림 개념을 명확하게 설명',
    'assessmentUser': 'No - 학생이 10과 2로 분해하는 것을 이해했다고 반응'},
    ```

생각 : 
- 물론, 기본적으로 제공되는 Built-in Prompt을 사용하더라도 유사한 결과를 얻을 수 있다. 다만, Memory가 좀 더 구체적인 정보들을 빠뜨리지 않고 수집하기를 원한다면 Prompt Override 방식을 사용하는것이 좋다.
- Raw Messages 데이터를 가지고 LTM을 만드는것이 아닌, Extraction을 통해 생성된 Turn을 가지고 Episode을 구성하고, 이를 통해 Reflection을 생성하는 것이다. 따라서 Raw Messages에서 추출된 Turn Data의 의존성이 높을 수밖에 없다.

