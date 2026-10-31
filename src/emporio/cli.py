"""One in-memory customer session per CLI process."""
import argparse
import os
from pathlib import Path

from emporio.agent import Agent, Session
from emporio.data import StoreData
from emporio.policies import Policies
from emporio.provider import Ollama


def main():
    parser = argparse.ArgumentParser(description="Empório da Música read-only support prototype")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--policies", type=Path, required=True)
    parser.add_argument("--demo-customer-id", type=int,
                        help="Trusted demo identity, NOT production authentication")
    args = parser.parse_args()
    try:
        store = StoreData(args.data_dir)
        policies = Policies.from_pdf(args.policies)
        provider = Ollama(os.getenv("OLLAMA_MODEL", "qwen3:8b"),
                          os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"Invalid local data/configuration: {exc}\n")
    agent = Agent(store, policies, provider)
    session = Session(customer_id=args.demo_customer_id)
    print(f"Demo only. CSV snapshot: {store.snapshot_id}. No stock reservations. /quit to exit.")
    print("Olá! Sou o assistente virtual da Empório da Música. Como posso ajudar?")
    while True:
        try:
            text = input("You> ").strip()
            if text == "/quit":
                break
            if text:
                print("Assistant>", agent.respond(session, text))
        except (EOFError, KeyboardInterrupt):
            print()
            break
        except ValueError as exc:
            print(str(exc))


if __name__ == "__main__":
    main()
