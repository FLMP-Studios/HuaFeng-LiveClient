import tkinter.ttk as ttk
import tkinter
from PIL import Image, ImageTk
from ffpyplayer.player import MediaPlayer
import asyncio
import threading
import backend
import concurrent.futures
import aiohttp
from time import sleep
import io


# 定义视频播放器类
class VideoPlay:
    # 初始化函数
    def __init__(self, videoSource: str, anchor: str) -> None:
        self.root: tkinter.Toplevel = tkinter.Toplevel()
        self.root.title(f'{anchor}的直播')  # 设置窗口标题

        # 创建一个画布用于显示视频帧
        self.canvas: tkinter.Canvas = tkinter.Canvas(self.root, bg='black')
        self.canvas.pack(fill=tkinter.BOTH, expand=True)

        # 创建暂停/播放按钮
        self.pause_button: ttk.Button = ttk.Button(self.root, text='开始/暂停', command=self.toggle_pause)
        self.pause_button.pack(side=tkinter.LEFT)

        # 初始化播放器和播放状态标志
        self.player: MediaPlayer = None
        self.is_paused: bool = False

        # 开始播放视频
        self.start_video(videoSource)
        print(f"开始播放视频: {videoSource}")  # 添加调试信息
        try:
            self.root.mainloop()
        except:
            ...

    # 开始播放视频的函数
    def start_video(self, source: str) -> None:
        self.player = MediaPlayer(source)  # 创建一个MediaPlayer对象
        while True:
            if self.is_paused:
                sleep(0.1)
                continue

            frame, val = self.player.get_frame()  # 获取下一帧和帧间隔
            if val == 'eof':
                self.player = None  # 如果视频结束，释放播放器资源
                break
            elif frame is None:
                sleep(0.01)  # 如果没有帧，重试
                continue

            # 将帧图像转换为ttk PhotoImage并显示在画布上
            image, pts = frame
            image = Image.frombytes("RGB", image.get_size(), bytes(image.to_bytearray()[0]))

            # 获取窗口大小并按比例缩放图像
            try:
                window_width: int = self.canvas.winfo_width()
                window_height: int = self.canvas.winfo_height()
                image.thumbnail((window_width, window_height))
            
                photo: ImageTk.PhotoImage = ImageTk.PhotoImage(image=image)
                self.canvas.create_image(0, 0, image=photo, anchor=tkinter.NW)
                self.canvas.image = photo  # 保持对PhotoImage的引用以防止垃圾回收
            except:
                self.player.set_pause(self.is_paused)
                self.player = None
                self.root.destroy()
                del self
                break

            sleep(val)

    # 切换暂停状态的函数
    def toggle_pause(self) -> None:
        if self.player:
            self.is_paused = not self.is_paused  # 切换暂停状态
            self.player.set_pause(self.is_paused)  # 设置播放器暂停状


class MainWindow:
    def __init__(self):
        self.ask_window = AskWindow()
        self.ask_window.wait_window()
        self.base_url = self.ask_window.base_url
        self.token = self.ask_window.token

        self.root = tkinter.Tk()
        self.__win()
        self.tk_label_frame_m70090d2 = self.__tk_label_frame_m70090d2(self.root) 
        self.tk_list_box_m7009mg6 = self.__tk_list_box_m7009mg6(self.tk_label_frame_m70090d2)  # 直播列表
        self.tk_frame_m700adhb = self.__tk_frame_m700adhb(self.root)  
        self.tk_canvas_m700csgf = self.__tk_canvas_m700csgf(self.tk_frame_m700adhb) 
        self.tk_button_m700bxy8 = self.__tk_button_m700bxy8(self.root)
        self.tk_label_frame_m700yzw9 = self.__tk_label_frame_m700yzw9(self.root)
        self.tk_list_box_m700arav = self.__tk_list_box_m700arav(self.tk_label_frame_m700yzw9) 

        self.processor = backend.MainProcessor(baseURL=self.base_url, token=self.token)  # 初始化MainProcessor
        self.root.after(0, self.run_async_tasks)

    def run_async_tasks(self):
        threading.Thread(target=self.load_live_list).start()

    def load_live_list(self):
        asyncio.run(self._load_live_list())

    async def _load_live_list(self):
        live_list = await self.processor.getLiveList()
        if live_list:
            for live in live_list:
                self.tk_list_box_m7009mg6.insert(tkinter.END, f"{live['name']} - {live['author']}")
        self.tk_list_box_m7009mg6.bind('<<ListboxSelect>>', self.display_live_info)

    def display_live_info(self, event):
        threading.Thread(target=self._display_live_info_thread, args=(event,)).start()

    def _display_live_info_thread(self, event):
        asyncio.run(self._display_live_info(event))

    async def _display_live_info(self, event):
        selected_index = self.tk_list_box_m7009mg6.curselection()
        if selected_index:
            live_name = self.tk_list_box_m7009mg6.get(selected_index)
            live_id = await self.get_live_id_by_name(live_name.split(" - ")[0])
            if live_id:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    live_list_future = executor.submit(asyncio.run, self.processor.getLiveList())
                    live_list = live_list_future.result()
                    live_details = next((live for live in live_list if live['id'] == live_id), None)
                    if live_details:
                        self.tk_list_box_m700arav.delete(0, tkinter.END)
                        self.tk_list_box_m700arav.insert(tkinter.END, f"直播间名: {live_details['name']}")
                        self.tk_list_box_m700arav.insert(tkinter.END, f"主播: {live_details['author']}")
                        self.tk_list_box_m700arav.insert(tkinter.END, f"直播间人数: {live_details['peoples']}")
                        self.tk_list_box_m700arav.insert(tkinter.END, f"描述: {live_details['description']}")
                        
                        try:
                            # 绘制直播封面
                            if live_details['pic']:
                                async with aiohttp.ClientSession() as session:
                                    async with session.get(live_details['pic']) as response:
                                        data = await response.read()  # 使用二进制模式读取数据
                                        image = Image.open(io.BytesIO(data))  # 将数据转换为图像对象
                                        
                                        # 获取Canvas的大小
                                        canvas_width = self.tk_canvas_m700csgf.winfo_width()
                                        canvas_height = self.tk_canvas_m700csgf.winfo_height()
                                        
                                        # 等比例缩放图片
                                        image.thumbnail((canvas_width, canvas_height))
                                        
                                        photo = ImageTk.PhotoImage(image=image)
                                        self.tk_canvas_m700csgf.create_image(0, 0, image=photo, anchor=tkinter.NW)
                                        self.tk_canvas_m700csgf.image = photo  # 保持对PhotoImage的引用以防止垃圾回收
                        except:
                            ...

    def enter_live(self):
        threading.Thread(target=self._enter_live_thread).start()

    def _enter_live_thread(self):
        asyncio.run(self._enter_live())

    async def _enter_live(self):
        selected_index = self.tk_list_box_m7009mg6.curselection()
        if selected_index:
            live_name = self.tk_list_box_m7009mg6.get(selected_index)
            live_id = await self.get_live_id_by_name(live_name.split(" - ")[0])
            if live_id:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    video_source_future = executor.submit(asyncio.run, self.processor.getLiveSource(live_id))
                    video_source = video_source_future.result()
                    if video_source:
                        VideoPlay(videoSource=video_source, anchor=live_name.split(" - ")[1])

    async def get_live_id_by_name(self, name):
        live_list = await self.processor.getLiveList()
        for live in live_list:
            if live['name'] == name:
                return live['id']
        return None

    def __win(self):
        self.root.title("花枫Live")
        # 设置窗口大小、居中
        width = 550
        height = 320
        screenwidth = self.root.winfo_screenwidth()
        screenheight = self.root.winfo_screenheight()
        geometry = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        self.root.geometry(geometry)
        
        self.root.minsize(width=width, height=height)
        
    def scrollbar_autohide(self, vbar, hbar, widget):
        """自动隐藏滚动条"""
        def show():
            if vbar: vbar.lift(widget)
            if hbar: hbar.lift(widget)
        def hide():
            if vbar: vbar.lower(widget)
            if hbar: hbar.lower(widget)
        hide()
        widget.bind("<Enter>", lambda e: show())
        if vbar: vbar.bind("<Enter>", lambda e: show())
        if vbar: vbar.bind("<Leave>", lambda e: hide())
        if hbar: hbar.bind("<Enter>", lambda e: show())
        if hbar: hbar.bind("<Leave>", lambda e: hide())
        widget.bind("<Leave>", lambda e: hide())
    
    def v_scrollbar(self, vbar, widget, x, y, w, h, pw, ph):
        widget.configure(yscrollcommand=vbar.set)
        vbar.config(command=widget.yview)
        vbar.place(relx=(w + x) / pw, rely=y / ph, relheight=h / ph, anchor='ne')
    def h_scrollbar(self, hbar, widget, x, y, w, h, pw, ph):
        widget.configure(xscrollcommand=hbar.set)
        hbar.config(command=widget.xview)
        hbar.place(relx=x / pw, rely=(y + h) / ph, relwidth=w / pw, anchor='sw')
    def create_bar(self, master, widget, is_vbar, is_hbar, x, y, w, h, pw, ph):
        vbar, hbar = None, None
        if is_vbar:
            vbar = ttk.Scrollbar(master)
            self.v_scrollbar(vbar, widget, x, y, w, h, pw, ph)
        if is_hbar:
            hbar = ttk.Scrollbar(master, orient="horizontal")
            self.h_scrollbar(hbar, widget, x, y, w, h, pw, ph)
        self.scrollbar_autohide(vbar, hbar, widget)

    def __tk_label_frame_m70090d2(self, parent):
        frame = ttk.LabelFrame(parent, text="直播列表",)
        frame.place(relx=0.0333, rely=0.0411, relwidth=0.3660, relheight=0.8418)
        return frame
    
    def __tk_list_box_m7009mg6(self, parent):
        lb = tkinter.Listbox(parent)
        
        lb.place(relx=0.0000, rely=0.0000, relwidth=1.0000, relheight=1.0000)
        return lb
    
    def __tk_frame_m700adhb(self, parent):
        frame = ttk.Frame(parent)
        frame.place(relx=0.4436, rely=0.0633, relwidth=0.3678, relheight=0.5063)
        return frame
    
    def __tk_canvas_m700csgf(self, parent):
        canvas = tkinter.Canvas(parent, bg="#aaa")
        canvas.place(relx=0.0000, rely=0.0000, relwidth=1.0000, relheight=1.0000)
        return canvas
    
    def __tk_button_m700bxy8(self, parent):
        btn = ttk.Button(parent, text="进去", takefocus=False, command=self.enter_live)
        btn.place(relx=0.8503, rely=0.0633, relwidth=0.1054, relheight=0.1139)
        return btn

    def __tk_label_frame_m700yzw9(self, parent):
        frame = ttk.LabelFrame(parent, text="直播间信息",)
        frame.place(relx=0.4436, rely=0.5728, relwidth=0.3660, relheight=0.3133)
        return frame
    
    def __tk_list_box_m700arav(self, parent):
        lb = tkinter.Listbox(parent)
        
        lb.place(relx=0.0000, rely=0.0000, relwidth=1.0000, relheight=1.0000)
        return lb
    
class AskWindow(tkinter.Tk):
    def __init__(self):
        super().__init__()

        self.geometry("400x150")
        self.title(" ")

        self.labelr8fs = ttk.Label(self, text="输入直播服务器地址")
        self.label3d3a = ttk.Label(self, text="例如: https://live.dfggmc.top/")
        self.textf3d0c = tkinter.Text(self, width=40, height=1)
        self.label8hsc = ttk.Label(self, text="输入用户 Token（未输入将无法发送弹幕、创建直播间等）")
        self.textdje2v = tkinter.Text(self, width=40, height=1)
        self.buttonf94 = ttk.Button(self, text="提交", command=self.getUserInput)

        self.textf3d0c.insert(tkinter.END, "https://live.dfggmc.top/")

        self.elements = [self.labelr8fs, self.label3d3a, self.textf3d0c, self.label8hsc, self.textdje2v, self.buttonf94]

        for element in self.elements:
            element.pack()

    def getUserInput(self):
        self.base_url = self.textf3d0c.get(1.0, tkinter.END).rstrip("\n")
        self.token = self.textdje2v.get(1.0, tkinter.END).rstrip("\n")
        self.destroy()