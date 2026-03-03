"""
CLI Interface for Dexter Vietnam - AI Trading Assistant
Sử dụng rich & click cho giao diện terminal đẹp
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env sớm
load_dotenv(Path(__file__).resolve().parent / ".env")

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.theme import Theme

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

console = Console(theme=Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
}))


BANNER = r"""
[bold cyan]
    
[/bold cyan][bold yellow]  Vietnam AI Trading Assistant 🇻🇳[/bold yellow]
"""

HELP_TEXT = """
[bold]Các lệnh:[/bold]
  [cyan]/help[/cyan]     - Hiển thị trợ giúp
  [cyan]/clear[/cyan]    - Xóa lịch sử hội thoại
  [cyan]/tools[/cyan]    - Liệt kê các tools có sẵn
  [cyan]/quit[/cyan]     - Thoát

[bold]Ví dụ câu hỏi:[/bold]
  • Phân tích VNM
  • Khối ngoại mua gì hôm nay?
  • Tin tức FPT
  • Lọc cổ phiếu giá trị
  • Thị trường hôm nay thế nào?
  • Định giá VCB bằng DCF
  • So sánh VNM và VCB
"""


def create_agent(model, api_key):
    """Create the AgentOrchestrator with error handling."""
    from dexter_vietnam.agent.orchestrator import AgentOrchestrator

    try:
        agent = AgentOrchestrator(
            model=model if model else None,
            api_key=api_key if api_key else None,
        )
        return agent
    except Exception as e:
        console.print(f"[error]Lỗi khởi tạo agent: {e}[/error]")
        console.print(
            "[warning]Kiểm tra OPENROUTER_API_KEY trong file .env hoặc truyền qua --api-key[/warning]"
        )
        sys.exit(1)


@click.group(invoke_without_command=True)
@click.option("--model", "-m", default=lambda: os.getenv("LLM_MODEL") or None, help="Model name (mặc định: đọc từ LLM_MODEL trong .env)")
@click.option("--api-key", "-k", default=None, help="OpenRouter API key override")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx, model, api_key, debug):
    """Dexter Vietnam - AI Trading Assistant cho chứng khoán Việt Nam"""
    ctx.ensure_object(dict)
    ctx.obj["model"] = model
    ctx.obj["api_key"] = api_key

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("dexter_vietnam").setLevel(logging.DEBUG)

    if ctx.invoked_subcommand is None:
        ctx.invoke(chat)


@cli.command()
@click.pass_context
def chat(ctx):
    """Chế độ chat tương tác với Dexter"""
    console.print(BANNER)
    console.print(Panel(
        "[bold]Chào mừng đến với Dexter! Gõ câu hỏi hoặc /help để xem hướng dẫn.[/bold]",
        border_style="cyan",
    ))

    model = ctx.obj.get("model") or os.getenv("LLM_MODEL") or None
    api_key = ctx.obj.get("api_key")

    with console.status("[cyan]Đang khởi tạo agent...[/cyan]", spinner="dots"):
        agent = create_agent(model, api_key)

    tools_count = len(agent.registry.get_tool_names())
    console.print(
        f"[success]✅ Sẵn sàng! Model: {agent.llm.model} | Tools: {tools_count}[/success]\n"
    )

    # Interactive loop
    while True:
        try:
            query = Prompt.ask("[bold cyan]Bạn[/bold cyan]")
            query = query.strip()

            if not query:
                continue

            # Handle commands
            if query.startswith("/"):
                cmd = query.lower()
                if cmd in ("/quit", "/exit", "/q"):
                    console.print("[info]Tạm biệt! 👋[/info]")
                    break
                elif cmd == "/help":
                    console.print(HELP_TEXT)
                    continue
                elif cmd == "/clear":
                    agent.memory.clear()
                    console.print("[success]Đã xóa lịch sử hội thoại.[/success]")
                    continue
                elif cmd == "/tools":
                    tools = agent.registry.get_all_tools()
                    console.print("\n[bold]📦 Tools có sẵn:[/bold]")
                    for name, tool in tools.items():
                        desc = tool.get_description().split("\n")[0][:80]
                        console.print(f"  [cyan]{name}[/cyan]: {desc}")
                    console.print()
                    continue
                else:
                    console.print(f"[warning]Lệnh không hợp lệ: {query}. Gõ /help[/warning]")
                    continue

            # Process query (synchronous - no asyncio.run needed)
            with console.status(
                "[cyan]🔍 Đang phân tích...[/cyan]", spinner="dots"
            ):
                response = agent.chat(query)

            # Display response
            console.print()
            console.print(Panel(
                Markdown(response),
                title="[bold yellow]🤖 Dexter[/bold yellow]",
                border_style="yellow",
                padding=(1, 2),
            ))
            console.print()

        except KeyboardInterrupt:
            console.print("\n[info]Tạm biệt! 👋[/info]")
            break
        except EOFError:
            break
        except Exception as e:
            console.print(f"[error]Lỗi: {e}[/error]")


@cli.command()
@click.argument("query")
@click.pass_context
def ask(ctx, query):
    """Hỏi Dexter một câu hỏi đơn (không tương tác)"""
    model = ctx.obj.get("model") or os.getenv("LLM_MODEL") or None
    api_key = ctx.obj.get("api_key")

    with console.status("[cyan]Đang khởi tạo...[/cyan]", spinner="dots"):
        agent = create_agent(model, api_key)

    with console.status("[cyan]🔍 Đang phân tích...[/cyan]", spinner="dots"):
        response = agent.chat(query)

    console.print(Markdown(response))


@cli.command()
@click.pass_context
def tools(ctx):
    """Liệt kê tất cả tools có sẵn"""
    from dexter_vietnam.tools.registry import register_all_tools

    with console.status("[cyan]Đang tải tools...[/cyan]", spinner="dots"):
        registry = register_all_tools()

    console.print("\n[bold]📦 Dexter Vietnam Tools:[/bold]\n")
    for name, tool in registry.get_all_tools().items():
        desc = tool.get_description().strip()
        console.print(Panel(
            desc,
            title=f"[bold cyan]{name}[/bold cyan]",
            border_style="cyan",
            padding=(0, 1),
        ))
    console.print(f"\n[success]Tổng: {len(registry.get_tool_names())} tools[/success]")


def main():
    """Entry point"""
    cli(obj={})


if __name__ == "__main__":
    main()
