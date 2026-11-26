"""Conservative language checks for consent-dependent privacy conclusions.

These checks reject unsafe assertions; they do not establish legality or replace
the separate semantic fact audit. Absence of proof is never proof of no consent.
"""
import re

CASE=re.compile(r'甲公司|乙公司|丙公司|丁公司|本案|题设|该受托人')
PRIVACY=re.compile(r'个人信息|转委托|处理目的|同意|授权')
CONCLUSION=re.compile(r'违反|违法|构成侵权|构成违约|有权(?:要求|请求)[^。；]{0,30}(?:停止|删除)')
UNKNOWN=re.compile(r'尚未(?:确认|查明|核实)|未(?:确认|查明|核实)|(?:是否|有无)[^。；]{0,40}(?:未知|不明|不确定)|事实[^。；]{0,10}(?:未知|不明)')
DENIED_CONSENT=re.compile(r'未经[^，。；]{0,18}(?:同意|授权)|未(?:取得|获得)[^，。；]{0,18}(?:同意|授权)|明确拒绝[^，。；]{0,12}(?:同意|授权)')
CONDITION=re.compile(r'^(?:(?:甲|乙|丙|丁)公司)?(?:若|如果|假如|倘若|如经查明|如确认|在(?:确认|查明|证实))')


def established_denial(question):
    for sentence in re.split(r'[。；;]',question or ''):
        for clause in re.split(r'[，,]',sentence):
            if DENIED_CONSENT.search(clause) and not UNKNOWN.search(clause) and not CONDITION.match(clause.strip()) and not re.search(r'若|如果|假如|是否|如未',clause):
                return True
    return False


def language_issues(statement,question):
    errors=[]
    if not CASE.search(statement) or not PRIVACY.search(statement):return errors
    for sentence in re.split(r'[。；;]',statement):
        conclusion=CONCLUSION.search(sentence)
        if not conclusion:continue
        prefix=sentence[:conclusion.start()].strip()
        # Only a condition governing this conclusion and mentioning consent can
        # qualify a consent-dependent conclusion. An unrelated "if" cannot.
        antecedent=re.split(r'[，,]',prefix,maxsplit=1)[0]
        conditional=bool(CONDITION.match(antecedent) and re.search(r'同意|授权',antecedent))
        if conditional:continue
        if UNKNOWN.search(statement):
            errors.append('事实语言检查：同意或授权尚未确认，却先对本案作出违法或救济权的确定判断；句末免责声明不能修复前文断言。')
        elif not established_denial(question):
            errors.append('事实语言检查：原问题没有确认未经同意或授权，不能从未披露第三方等事实直接认定本案个人信息处理违法；应先表述待核实条件。')
    return list(dict.fromkeys(errors))
