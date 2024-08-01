casuals = [
    {
        "title": "今天天气怎么样",
    },
    {
        "raw": "今天天气怎么样",
    },
]

features = [
    {
        "title": "如何理解分布式事务",
    },
    {
        "raw": "如何理解分布式事务",
    },
]

diagnostic = [
    {
        "title": "OB 停电重启之后无法连接了怎么办？",
    },
    {
        "raw": "OB 停电重启之后无法连接了怎么办？",
    },
]

diagnostic2 = [
    {
        "title": "OB 停电重启之后无法连接了怎么办？",
    },
    {
        "raw": "OB 停电重启之后无法连接了怎么办？",
    },
    {
        "raw": """
日志采集场景: 集群无法连接
日志采集命令: obdiag gather run --scene=observer.cluster_down
根因分析场景: 未能明确问题的场景
根因分析命令: 无

**解释说明：**

根据您的问题描述，OceanBase在停电后重启出现了无法连接的情况。首先，我们建议您使用以下日志采集命令来收集集群的基础信息和可能的错误日志：

```shell
obdiag gather run --scene=observer.cluster_down
```

这条命令将帮助我们获取集群无法连接问题相关的所有必要日志和状态信息，这对于诊断为何集群无法正常访问至关重要。

由于直接指出了是“无法连接”的问题，而没有具体的错误代码或是更细致的报错描述，因此在当前阶段进行根因分析的精确场景选择比较困难。所以，针对此问题，我们暂不提供特定的根因分析命令。待日志收集完成后，根据日志内容再决定是否需要进一步的根因分析或采取其他诊断措施。

请执行上述日志采集命令，并将生成的日志文件（通常会是一个压缩包）提供给我们，这将有助于我们更深入地分析问题所在并给出针对性的解决建议。如果您在操作过程中遇到任何问题，也欢迎随时反馈。""",
    },
    {
        "raw": "谢谢老师，这是我采集到的日志，请您帮忙看看\n[observer.log.zip|attachment](upload://vdcAghHEu7gvuVMgGGLl9KRcDbN.zip) (860.1 KB)",
        "cooked": '谢谢老师，这是我采集到的日志，请您帮忙看看 <p><a class="attachment" href="/uploads/short-url/vdcAghHEu7gvuVMgGGLl9KRcDbN.zip">observer.log.zip</a> (860.1 KB)</p>',
    },
]

diagnostic3 = [
    {
        "title": "OB 停电重启之后无法连接了怎么办？",
    },
    {
        "raw": "OB 停电重启之后无法连接了怎么办？这是我拿到的日志 [observer.log.zip|attachment](upload://vdcAghHEu7gvuVMgGGLl9KRcDbN.zip) (860.1 KB)",
        "cooked": 'OB 停电重启之后无法连接了怎么办？<p><a class="attachment" href="/uploads/short-url/vdcAghHEu7gvuVMgGGLl9KRcDbN.zip">observer.log.zip</a> (860.1 KB)</p>',
    },
]

features2 = [
    {"title": "官方文档中《并发控制概述》的疑问"},
    {
        "raw": """疑问一：提交请求处理那里，提到如下内容。这里的"本地提交时间戳"到底是等于最大读时间戳，还是等于 最大读时间戳与GTS取值这二者中的MAX？

> 当事务提交时，我们会走对应的两阶段提交，我们对于参与者中的每一个分区取本地 最大读时间戳 作为本地提交时间戳。这个保证是为了做单值的读写冲突（anti dependency），根据保证，可以得到我们的提交时间戳一定大于之前所有的读取，因此我们在串行执行中可以在这些之前的读取后面。如图所示，事务 12 进入提交阶段，并设置状态为 PREPARE，设置本地事务版本号为本地 最大读时间戳 120 与取 GTS 为 150 的最大值 150 作为 本地事务版本号

疑问二： 写请求处理那里，提到如下内容。SI隔离级别下为防止丢失更新，会用读时间戳与本行上的ts进行比较，如果前者小于后者，则事务会回滚。这里"写操作的读时间戳"指的是什么？

> 快照读隔离级别为了防止读写冲突（anti dependency）和写读请求（read dependency）成环，即丢失更新(lost update)，尽管写入或唤醒后加锁成功，会用读时间戳，跟本行上维护的 最大提交事务时间戳 作比较，如果读时间戳小于行上的最大提交事务时间，则会回滚掉此事务。比如说若上图写操作的读时间戳是 100，事务 12 以时间戳 160 提交，那么就会触发写操作对应事务的回滚，对应的报错(TRANSACTION_SET_VIOLATION )""",
    },
]

"""
features2: 
根据文档库中的信息，针对您的疑问，解答如下：

疑问一：提交请求处理时，"本地提交时间戳"实际上是等于最大读时间戳与GTS取值这二者中的MAX。具体来说，当事务提交时，系统会取本地最大读时间戳，并与从GTS获取的时间戳进行比较，选取这两者中的较大值作为本地提交时间戳。这样可以确保事务的提交时间戳不仅反映了事务自身的读操作，还考虑了全局时间进展，从而保证了事务之间的时间顺序性，有效避免了读写冲突。

疑问二：在SI隔离级别下，"写操作的读时间戳"指的是该写事务在开始时从GTS获取的读时间戳。这个时间戳用于在事务提交前验证事务读取的数据版本是否仍然有效，即检查在事务读取数据后是否有其他事务已经提交了对该数据的新版本。如果写事务的读时间戳小于当前数据行上维护的最大提交事务时间戳，表明在该事务读取之后有其他事务已经对此数据进行了修改并提交，为了防止丢失更新，此时当前事务会被回滚，以确保数据的一致性。
具体信息可参考以下文档:
- [100.concurrency-control-overview.md](https://github.com/oceanbase/oceanbase-doc/blob/V4.1.0/zh-CN/700.reference/100.oceanbase-database-concepts/800.transaction-management/200.transaction-concurrency-and-consistency/300.concurrency-control/100.concurrency-control-overview.md)
- [400.global-timestamp.md](https://github.com/oceanbase/oceanbase-doc/blob/V4.1.0/zh-CN/700.reference/100.oceanbase-database-concepts/800.transaction-management/100.transaction/400.global-timestamp.md)
- [200.multi-version-read-consistency.md](https://github.com/oceanbase/oceanbase-doc/blob/V4.1.0/zh-CN/700.reference/100.oceanbase-database-concepts/800.transaction-management/200.transaction-concurrency-and-consistency/200.multi-version-read-consistency.md)
- [300.system-architecture.md](https://github.com/oceanbase/oceanbase-doc/blob/V4.1.0/zh-CN/100.learn-more-about-oceanbase/300.system-architecture.md)
- [200.lock-mechanism.md](https://github.com/oceanbase/oceanbase-doc/blob/V4.1.0/zh-CN/700.reference/100.oceanbase-database-concepts/800.transaction-management/200.transaction-concurrency-and-consistency/300.concurrency-control/200.lock-mechanism.md)
- [500.weak-consistency-reading.md](https://github.com/oceanbase/oceanbase-doc/blob/V4.1.0/zh-CN/700.reference/100.oceanbase-database-concepts/800.transaction-management/200.transaction-concurrency-and-consistency/500.weak-consistency-reading.md)
"""

import requests
import random
from datetime import datetime


def generate_topic(title: str) -> dict:
    user_id = random.randint(10000, 99999)
    time_now = datetime.now().isoformat()
    return {
        "topic": {
            "tags": [],
            "tags_descriptions": {},
            "id": random.randint(1000000, 9999999),
            "title": title,
            "fancy_title": title,
            "posts_count": 1,
            "created_at": time_now,
            "views": 0,
            "reply_count": 0,
            "like_count": 0,
            "last_posted_at": time_now,
            "visible": True,
            "closed": False,
            "archived": False,
            "archetype": "regular",
            "slug": "topic",
            "category_id": 21,
            "word_count": 18,
            "deleted_at": None,
            "user_id": user_id,
            "featured_link": None,
            "pinned_globally": False,
            "pinned_at": None,
            "pinned_until": None,
            "unpinned": None,
            "pinned": False,
            "highest_post_number": 1,
            "deleted_by": None,
            "has_deleted": False,
            "bookmarked": False,
            "participant_count": 1,
            "thumbnails": None,
            "created_by": {
                "id": user_id,
                "username": "与义",
                "name": "与义",
                "avatar_template": "/letter_avatar_proxy/v4/letter/%E4%B8%8E/7CB305/{size}.png",
                "assign_icon": "user-plus",
                "assign_path": "/u/与义/activity/assigned",
            },
            "last_poster": {
                "id": user_id,
                "username": "与义",
                "name": "与义",
                "avatar_template": "/letter_avatar_proxy/v4/letter/%E4%B8%8E/7CB305/{size}.png",
                "assign_icon": "user-plus",
                "assign_path": "/u/与义/activity/assigned",
            },
            "tags_disable_ads": False,
        }
    }


def generate_post(
    **kwargs,
) -> dict:
    name = kwargs.get("name", "与义")
    raw = kwargs.get("raw")
    cooked = kwargs.get("cooked", raw)
    post_number = kwargs.get("post_number", 1)
    topic_id = kwargs.get("topic_id", 1000000)
    user_id = kwargs.get("user_id", 33271)
    time_now = datetime.now().isoformat()
    return {
        "post": {
            "id": random.randint(10000, 99999),
            "name": name,
            "username": name,
            "avatar_template": "/letter_avatar_proxy/v4/letter/%E4%B8%8E/7CB305/{size}.png",
            "created_at": time_now,
            "cooked": cooked,
            "post_number": post_number,
            "post_type": 1,
            "updated_at": time_now,
            "reply_count": 0,
            "reply_to_post_number": None,
            "quote_count": 0,
            "incoming_link_count": 0,
            "reads": 0,
            "score": 0,
            "topic_id": topic_id,
            "topic_slug": "topic",
            "category_id": 21,
            "display_username": name,
            "primary_group_name": None,
            "flair_name": None,
            "version": 1,
            "user_title": None,
            "bookmarked": False,
            "raw": raw,
            "moderator": True,
            "admin": True,
            "staff": True,
            "user_id": user_id,
            "hidden": False,
            "trust_level": 4,
            "deleted_at": None,
            "user_deleted": False,
            "edit_reason": None,
            "wiki": False,
            "reviewable_id": None,
            "reviewable_score_count": 0,
            "reviewable_score_pending_count": 0,
            "topic_posts_count": 1,
            "topic_filtered_posts_count": 1,
            "topic_archetype": "regular",
            "category_slug": "oceanbase",
        }
    }


def make_requests(messages: list[dict]):
    topic = generate_topic(messages[0]["title"])
    requests.post("http://127.0.0.1:8000/repost/entry", json=topic)

    user_id = random.randint(6000, 7000)
    bot_id = random.randint(3000, 4000)
    bot_name = "机器人"

    for i, msg in enumerate(messages[1:]):
        if i % 2 == 0:
            requests.post(
                "http://127.0.0.1:8000/repost/entry",
                json=generate_post(
                    topic_id=topic["topic"]["id"],
                    post_number=i + 1,
                    user_id=user_id,
                    **msg,
                ),
            )
        else:
            requests.post(
                "http://127.0.0.1:8000/repost/entry",
                json=generate_post(
                    topic_id=topic["topic"]["id"],
                    post_number=i + 1,
                    user_id=bot_id,
                    name=bot_name,
                    **msg,
                ),
            )


if __name__ == "__main__":

    make_requests(features2)
