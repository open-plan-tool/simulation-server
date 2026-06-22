import os
import json
import uuid
import asyncio
import websockets
import pika
import redis
import time
import traceback
from typing import Optional

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbitmq")
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
MOSAIK_WS_URL = os.environ.get("MOSAIK_WS_URL", "ws://mosaik-orbit:8442")
RESULTS_DIR = os.environ.get("RESULTS_DIR", "/data/results")
RESOURCES_DIR = os.environ.get("RESOURCES_DIR", "/data/resources")
MOSAIK_QUEUE = os.environ.get("MOSAIK_QUEUE", "mosaik_requests")


def connect_rabbitmq():
    while True:
        try:
            rmq = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            return rmq
        except pika.exceptions.AMQPConnectionError:
            print("Waiting for RabbitMQ...")
            time.sleep(3)


def connect_redis():
    return redis.Redis(host=REDIS_HOST, port=6379, db=0)


async def run_mosaik_simulation(scenario: dict, task_id: str) -> dict:
    result = {"status": "success", "task_id": task_id}
    logs = []
    orbit = None
    sim_progress = 0.0

    try:
        async with websockets.connect(MOSAIK_WS_URL) as ws:
            print(f"[{task_id}] Connected to mosaik-orbit WebSocket")

            starters = await ws.recv()
            print(f"[{task_id}] Received AvailableStarters greeting")

            bake_id = str(uuid.uuid4())
            bake_msg = {"$type": "Bake", "id": bake_id, "scenario": scenario}
            await ws.send(json.dumps(bake_msg))
            print(f"[{task_id}] Sent Bake message (id={bake_id})")

            while True:
                response = await ws.recv()
                msg = json.loads(response)
                msg_type = msg.get("$type", "")

                if msg_type == "UpdateOrbit" and msg["id"] == bake_id:
                    orbit = msg["orbit"]
                    print(f"[{task_id}] Bake complete")
                    break

                if msg_type == "BakeFailed" and msg["id"] == bake_id:
                    raise Exception(f"Bake failed: {msg['message']}")

                if msg_type == "Log":
                    logs.append(msg["entry"])

                if msg_type == "UpdateSimulationProgress":
                    sim_progress = msg.get("sim_progress", sim_progress)

            await ws.send(json.dumps({"$type": "StartSimulation"}))
            print(f"[{task_id}] Sent StartSimulation message")

            sim_status = None
            while sim_status != "complete":
                response = await ws.recv()
                msg = json.loads(response)
                msg_type = msg.get("$type", "")

                if msg_type == "UpdateSimulationStatus":
                    sim_status = msg["status"]
                    print(f"[{task_id}] Simulation status: {sim_status}")
                    if sim_status == "idle":
                        raise Exception("Simulation did not start")

                if msg_type == "UpdateSimulationProgress":
                    sim_progress = msg.get("sim_progress", sim_progress)

                if msg_type == "Log":
                    logs.append(msg["entry"])

            result["orbit"] = orbit
            result["logs"] = logs
            result["sim_progress"] = sim_progress

    except Exception as e:
        result["status"] = "error"
        result["error"] = traceback.format_exc()
        result["logs"] = logs

    return result


def on_request(ch, method, props, body):
    task_id = None
    try:
        msg = json.loads(body)
        task_id = msg["task_id"]
        scenario = msg["scenario"]
        print(f"[{task_id}] Received task")

        r = connect_redis()
        r.hset(f"task:{task_id}", "status", "RUNNING")

        scenario_path = os.path.join(RESOURCES_DIR, task_id, "scenario.json")
        if os.path.exists(scenario_path):
            with open(scenario_path, "r") as f:
                scenario = json.load(f)

        result = asyncio.run(run_mosaik_simulation(scenario, task_id))

        result_dir = os.path.join(RESULTS_DIR, task_id)
        os.makedirs(result_dir, exist_ok=True)
        output_file = "result.json"
        with open(os.path.join(result_dir, output_file), "w") as f:
            json.dump(result, f)

        if result["status"] == "success":
            r.hset(f"task:{task_id}", mapping={"status": "DONE", "files": json.dumps([output_file])})
        else:
            r.hset(f"task:{task_id}", mapping={"status": "ERROR", "error": result.get("error", "Unknown error")})

        print(f"[{task_id}] Finished task with status: {result['status']}")

    except Exception as e:
        print(f"Error processing task {task_id}: {traceback.format_exc()}")
        if task_id:
            r = connect_redis()
            r.hset(f"task:{task_id}", mapping={"status": "ERROR", "error": str(e)})

    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    print("Starting mosaik worker...")

    rmq = connect_rabbitmq()
    channel = rmq.channel()
    channel.queue_declare(queue=MOSAIK_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)

    print(f"Listening on queue: {MOSAIK_QUEUE}")
    channel.basic_consume(queue=MOSAIK_QUEUE, on_message_callback=on_request)
    channel.start_consuming()


if __name__ == "__main__":
    main()