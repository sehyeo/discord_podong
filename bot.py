import discord
import yt_dlp as youtube_dl
from discord.ext import commands
from token1 import TOKEN

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description='디스코드 입장을 위한 테스트 코드',
    intents=intents,
)

@bot.event
async def on_ready():
 print('{0.user}을 실행합니다.'.format(bot))

@bot.command(aliases=['입장'])
async def join(ctx):
    embed = discord.Embed(title="디스코드 봇 도우미(개발용)", description="음성 채널 개발용 디스코드 봇", color=0x00ff56)
    # 사용자가 음성 채널에 연결되어 있는지 확인
    if ctx.author.voice is None:
        embed.add_field(name=':exclamation:', value="음성 채널에 유저가 존재하지 않습니다. 1명 이상 입장해주세요.")
        await ctx.send(embed=embed)
        raise commands.CommandInvokeError("사용자가 존재하는 음성 채널을 찾지 못했습니다.")

    channel = ctx.author.voice.channel

    # 봇이 이미 음성 채널에 연결되어 있는 경우
    if ctx.voice_client is not None:
        embed.add_field(name=":robot:", value="사용자가 있는 채널로 이동합니다.", inline=False)
        await ctx.send(embed=embed)
        print("음성 채널 정보: {0.author.voice}".format(ctx))
        print("음성 채널 이름: {0.author.voice.channel}".format(ctx))
        return await ctx.voice_client.move_to(channel)

    # 봇이 음성 채널에 연결되지 않은 경우
    await channel.connect()


@bot.command(aliases=['퇴장'])
async def out(ctx):
    try:
        # 봇이 음성 채널에 연결되어 있는지 확인
        if ctx.voice_client is None:
            await ctx.send("봇이 연결된 음성 채널이 없습니다.")
            return

        embed = discord.Embed(color=0x00ff56)
        embed.add_field(name=":regional_indicator_b::regional_indicator_y::regional_indicator_e:",value=" {0.author.voice.channel}에서 내보냈습니다.".format(ctx),inline=False)
        # 음성 채널에서 봇 연결 끊기
        await bot.voice_clients[0].disconnect()
        await ctx.send(embed=embed)
    except AttributeError as not_found_channel:
        # 채널을 찾지 못한 경우
        print(f"에러 발생: {not_found_channel}")
        embed = discord.Embed(color=0xf66c24)
        embed.add_field(name=":grey_question:",
                        value="{0.author.voice.channel}에 유저가 존재하지 않거나 봇이 존재하지 않습니다.\\n다시 입장후 퇴장시켜주세요.".format(ctx),
                        inline=False)
        await ctx.send(embed=embed)
    except Exception as error_message:
        # 예상하지 못한 다른 에러
        print(f"에러 발생: {error_message}")
        embed = discord.Embed(color=0xf66c24)
        embed.add_field(name=":x:", value="봇이 존재하는 채널을 찾는 데 실패했습니다.")
        await ctx.send(embed=embed)

# 음악 재생 클래스
class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.current_player = None
        self.max_queue_size = 10  # 대기열 최대 길이 설정

    @commands.command(aliases=["입장"])
    async def join(self, ctx):
        """음성 채널에 입장합니다"""
        if not ctx.author.voice:
            await ctx.send("음성 채널에 먼저 입장해주세요.")
            return

        channel = ctx.author.voice.channel

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()
        await ctx.send(f"{channel} 채널에 입장했습니다.")

    async def play_next(self, ctx):
        """다음 곡을 자동으로 재생합니다"""
        if len(self.queue) > 0:  # 대기열이 비어있지 않은지 확인
            await self.skip(ctx)

    @commands.command(aliases=["다음"])
    async def skip(self, ctx):
        """대기열에서 다음 곡을 재생합니다"""
        if not ctx.voice_client:
            await ctx.send("봇이 음성 채널에 연결되어 있지 않습니다.")
            return

        if not self.queue:  # 대기열이 비어있는지 확인
            await ctx.send("다음 재생할 곡이 대기열에 없습니다.\n음악을 계속 재생하시려면 음악을 추가해주세요.")
            return

        # 현재 재생중인 음악 중지
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

        try:
            current_url, current_title = self.queue.pop(0)  # 바로 대기열에서 제거

            async with ctx.typing():
                self.current_player = await YTDLSource.from_url(current_url, loop=self.bot.loop, stream=True)

                ctx.voice_client.play(self.current_player,
                                      after=lambda _: asyncio.run_coroutine_threadsafe(self.play_next(ctx),
                                                                                       self.bot.loop))

                await ctx.send(f'지금 재생 중: {self.current_player.title}')

        except Exception as e:
            await ctx.send(f"재생 중 오류가 발생했습니다: {str(e)}")
            print(f"재생 오류: {e}")
            # 오류 발생 시 대기열에 기존 재생 곡 추가
            if current_url and current_title:
                self.queue.insert(0, (current_url, current_title))

    @commands.command(aliases=["재생"])
    async def play(self, ctx, *, url):
        """URL에서 음악을 재생하고 대기열에 추가합니다"""

        try:
            if not ctx.author.voice:
                await ctx.send("음성 채널에 먼저 입장해주세요.")
                return

            if not ctx.voice_client:
                await ctx.author.voice.channel.connect()

            if len(self.queue) >= self.max_queue_size:
                await ctx.send(f"대기열이 가득 찼습니다. 최대 {self.max_queue_size}곡까지만 추가할 수 있습니다.")
                return

            # 추가하려는 곡의 정보를 미리 가져옴
            async with ctx.typing():
                player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
                self.queue.append((url, player.title))
                if not ctx.voice_client.is_playing():
                    await self.skip(ctx)
                else:
                    queue_info = f'대기열에 "{player.title}" 노래가 추가되었습니다.\n현재 대기열 ({len(self.queue)}곡):\n'
                    for i, (_, title) in enumerate(self.queue, 1):
                        queue_info += f"{i}. {title}\n"
                    await ctx.send(queue_info)

        except Exception as e:
            await ctx.send(f"음악을 추가하는 중 오류가 발생했습니다: {str(e)}")
            print(f"재생 오류: {e}")

    @commands.command(aliases=["음량", "볼륨", "소리"])
    async def volume(self, ctx, volume: int):
        """플레이어의 볼륨을 조절합니다"""

        if ctx.voice_client is None:
            return await ctx.send("음성 채널에 연결되어 있지 않습니다.")

        if not 0 <= volume <= 100:
            return await ctx.send("볼륨은 0에서 100 사이의 값이어야 합니다.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"볼륨이 {volume}%로 변경되었습니다")

    @commands.command()
    async def stop(self, ctx):
        """재생을 멈추고 음성 채널에서 나갑니다"""
        if not ctx.voice_client:
            await ctx.send("봇이 음성 채널에 연결되어 있지 않습니다.")
            return

        self.queue.clear()
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        await ctx.send("재생을 멈추고 채널에서 나갔습니다.")

    @commands.command()
    async def pause(self, ctx):
        """음악을 일시정지합니다"""
        if not ctx.voice_client:
            await ctx.send("봇이 음성 채널에 연결되어 있지 않습니다.")
            return

        if ctx.voice_client.is_paused() or not ctx.voice_client.is_playing():
            await ctx.send("음악이 이미 일시 정지 중이거나 재생 중이지 않습니다.")
            return

        ctx.voice_client.pause()
        await ctx.send("음악이 일시정지되었습니다.")

    @commands.command()
    async def resume(self, ctx):
        """일시정지된 음악을 다시 재생합니다"""
        if not ctx.voice_client:
            await ctx.send("봇이 음성 채널에 연결되어 있지 않습니다.")
            return

        if ctx.voice_client.is_playing() or not ctx.voice_client.is_paused():
            await ctx.send("음악이 이미 재생 중이거나 재생할 음악이 존재하지 않습니다.")
            return

        ctx.voice_client.resume()
        await ctx.send("음악이 다시 재생됩니다.")

    @commands.command(aliases=["q", "플레이리스트", "대기열"])
    async def queue(self, ctx):
        """현재 대기열을 보여줍니다"""
        if len(self.queue) == 0:
            await ctx.send("대기열이 비어있습니다.")
            return

        queue_list = f"현재 대기열 ({len(self.queue)}/{self.max_queue_size}곡):\n"
        for i, (_, title) in enumerate(self.queue, 1):
            queue_list += f"{i}. {title}\n"
        await ctx.send(queue_list)

    @commands.command()
    async def now(self, ctx):
        """현재 재생중인 음악의 제목을 보여줍니다"""
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await ctx.send("현재 재생 중인 음악이 없습니다.")
            return

        if self.current_player:
            await ctx.send(f"현재 재생 중: {self.current_player.title}")
        else:
            await ctx.send("현재 재생 중인 음악 정보를 가져올 수 없습니다.")

    @commands.command(aliases=["삭제", "제거"])
    async def remove(self, ctx, index: int):
        """대기열에서 특정 곡을 삭제합니다"""
        if len(self.queue) == 0:
            await ctx.send("대기열이 비어있습니다.")
            return

        if not 1 <= index <= len(self.queue):
            await ctx.send(f"올바른 번호를 입력해주세요. (1 ~ 대기열 길이`({len(self.queue)})`)")
            return

        _, removed_title = self.queue.pop(index - 1)
        await ctx.send(f"대기열에서 {index}번 곡 '{removed_title}'이(가) 제거되었습니다.")

    @play.before_invoke
    @skip.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("음성 채널에 먼저 입장해주세요.")
                raise commands.CommandError("사용자가 음성 채널에 연결되어 있지 않습니다.")


# 봇 실행
bot.run(TOKEN)