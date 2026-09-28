from app.api.docs.responses import error_response
from app.core.exceptions import InvalidTokenError

_unauthorized_response = error_response("인증 실패", InvalidTokenError)

get_dashboard_docs = dict(
    summary="대시보드 조회",
    description="로그인한 사용자의 회고 데이터 대시보드 지표를 조회 시점 기준으로 집계해 반환한다. "
    "application_count 는 전체 지원 현황 수, completed_retrospect_count 는 요약까지 완료된(COMPLETED) 회고 세션 수, "
    "self_blame_count 는 모든 회고 대화에서 AI가 감지한 자기비난 횟수의 합이다(진행 중인 회고 포함). "
    "weakness_keywords 는 반복 보완 키워드로, 완료 회고 분석의 보완점 태그(고정 9종)별로 "
    "그 태그가 나온 회고 수(count)를 세어 많이 나온 순 상위 3개만 담는다. 한 번 이상 나온 태그만 대상이라 "
    "3개 미만일 수 있으며, 동률이면 태그 정의 순서를 따른다. 고정 태그가 아닌 과거 자유문장 보완점은 집계하지 않는다. "
    "stage_results 는 전형 단계별 합격 현황으로, 도달한 지원이 1건 이상인 단계만 전형 순서대로 담는다. "
    "total_count 는 그 단계에 도달한 지원 수(진행중 + 합격 + 탈락)이며 대기(미도달) 단계는 세지 않는다. "
    "most_failed_stage 는 탈락 수가 가장 많은 단계이며, 동률이면 합격 수가 적은 단계, "
    "그래도 같으면 뒤 단계를 반환한다. 탈락 기록이 없으면 null이다.",
    responses={
        200: {"description": "대시보드 조회 성공"},
        401: _unauthorized_response,
    },
)
