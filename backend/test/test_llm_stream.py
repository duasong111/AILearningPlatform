#!/usr/bin/env python3
"""
直接测试 MiMo API 流式输出（绕过 Django）
用法: python test/test_llm_stream.py
"""
import time
import json
import os
import sys

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.dev'))

from openai import OpenAI


def test_stream():
    # 配置（与后端一致）
    api_key = os.getenv("MIMO_API_KEY")
    base_url = os.getenv("MIMO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
    model = os.getenv("MIMO_MODEL", "mimo-v2.5-pro")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    print(f"API: {base_url}")
    print(f"Model: {model}")
    print(f"{'='*60}\n")

    client = OpenAI(api_key=api_key, base_url=base_url)

    messages = [
        {"role": "system", "content": "你是小AI，一个专业的数据结构学习助手。"},
        {"role": "user", "content": "用简单的话解释什么是二叉搜索树，它的优点是什么"},
    ]

    print("请求发送中...\n")
    request_start = time.time()

    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        temperature=temperature,
        extra_body={"thinking": {"type": "disabled"}},
    )

    first_chunk_time = None
    chunks = []
    full_response = ""

    print("开始接收 chunk:\n")
    print(f"{'序号':<5} {'相对时间':<12} {'间隔':<10} {'内容'}")
    print("-" * 70)

    for i, chunk in enumerate(stream):
        now = time.time()

        if first_chunk_time is None:
            first_chunk_time = now

        if chunk.choices and chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            full_response += content

            relative = now - request_start
            interval = (now - (chunks[-1]["time"] if chunks else request_start)) * 1000

            chunks.append({
                "idx": len(chunks) + 1,
                "time": now,
                "relative": relative,
                "interval": interval,
                "content": content
            })

            # 显示 chunk 信息
            preview = content[:20].replace("\n", "\\n")
            print(f"{len(chunks):<5} {relative*1000:>8.1f}ms  {interval:>7.1f}ms  {preview}")

    request_end = time.time()

    # 统计分析
    print(f"\n{'='*60}")
    print("统计分析:")
    print(f"{'='*60}")

    ttft = first_chunk_time - request_start if first_chunk_time else 0
    total_time = request_end - request_start

    print(f"\n首字节延迟 (TTFT): {ttft*1000:.1f}ms")
    print(f"总响应时间: {total_time*1000:.1f}ms")
    print(f"Chunk 总数: {len(chunks)}")
    print(f"完整内容长度: {len(full_response)} 字符")
    print(f"生成速度: {len(full_response)/total_time:.1f} 字符/秒")

    if len(chunks) > 1:
        intervals = [c["interval"] for c in chunks[1:]]  # 排除第一个
        print(f"\nChunk 间隔统计:")
        print(f"  平均间隔: {sum(intervals)/len(intervals):.2f}ms")
        print(f"  最小间隔: {min(intervals):.2f}ms")
        print(f"  最大间隔: {max(intervals):.2f}ms")
        print(f"  中位数:   {sorted(intervals)[len(intervals)//2]:.2f}ms")

        # 间隔分布
        print(f"\n间隔分布:")
        buckets = {"<10ms": 0, "10-50ms": 0, "50-100ms": 0, "100-500ms": 0, ">500ms": 0}
        for interval in intervals:
            if interval < 10:
                buckets["<10ms"] += 1
            elif interval < 50:
                buckets["10-50ms"] += 1
            elif interval < 100:
                buckets["50-100ms"] += 1
            elif interval < 500:
                buckets["100-500ms"] += 1
            else:
                buckets[">500ms"] += 1

        for bucket, count in buckets.items():
            bar = "█" * count
            print(f"  {bucket:>10}: {bar} ({count})")

    print(f"\n完整回复:\n{full_response}")


if __name__ == "__main__":
    test_stream()
