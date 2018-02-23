import socket
import os ,json
import optparse
import getpass
import hashlib
import sys 

# 状态码
STATUS_CODE  = {
    250 : "Invalid cmd format, e.g: {'action':'get','filename':'test.py','size':344}", # 错误 格式
    251 : "Invalid cmd ",  #  错误命令
    252 : "Invalid auth data",  # 验证失败
    253 : "Wrong username or password",  # 用户名或者密码错误
    254 : "Passed authentication",  # 验证错误
}



class FTPClient(object):
    def __init__(self):

        # 临时user
        self.user = None

        # 创建parser实例
        parser = optparse.OptionParser()
        #添加 选项
        parser.add_option("-s","--server", dest="server", help="ftp server ip_addr")
        parser.add_option("-P","--port",type="int", dest="port", help="ftp server port")
        parser.add_option("-u","--username", dest="username", help="username")
        parser.add_option("-p","--password", dest="password", help="password")

        self.options , self.args = parser.parse_args()
        #校验合法性
        self.verify_args(self.options,self.args)
        # 创建链接
        self.make_connection()

    def make_connection(self):
        ''' 创建连接 '''
        self.sock = socket.socket()
        self.sock.connect((self.options.server,self.options.port))

    def verify_args(self, options,args):
        '''校验参数合法型'''

        if options.username is not None and options.password is not None:
            pass
        elif options.username is None and options.password is None:
            pass
        else:
            #options.username is None or options.password is None:
            exit("Err: username and password must be provided together..")

        if options.server and options.port:
            #print(options)
            if options.port >0 and options.port <65535:
                return True
            else:
                exit("Err:host port must in 0-65535")
        else:
            exit("Error:must supply ftp server address, use -h to check all available arguments.")

    def authenticate(self):
        '''用户验证'''
        # 如果 写参数的时候有username 就放进去做验证
        if self.options.username:
            print(self.options.username,self.options.password)
            return  self.get_auth_result(self.options.username, self.options.password)
        else:
            #如果参数中没有用户名密码
            retry_count = 0
            while retry_count <3:
                username = input("username:").strip()
                password = input("password:").strip()
                if self.get_auth_result(username,password):
                    return True
                retry_count += 1



    def get_auth_result(self,user,password):
        data = {'action':'auth',
                'username':user,
                'password':password}
        # 传值用户名密码给 服务器
        self.sock.send(json.dumps(data).encode())
        # 接受服务端的回复结果
        response = self.get_response()
        # 如果回复的结果状态码 为 254
        if response.get('status_code') == 254:
            print("Passed authentication!")
            # user 原本为空，赋值给当前用户
            self.user = user
            # 返回一个true
            return True
        else:
            print(response.get("status_msg"))

    def get_response(self):
        '''得到服务器端回复结果'''
        data = self.sock.recv(1024)
        #print("server res", data)
        #获取服务器的数据
        data = json.loads(data.decode())
        #返回数据
        return data



    def interactive(self):
        ''' 跟服务器通信'''
        # 首先用户认证 如果成功就返回True 如果不成功就为空
        if self.authenticate():
            print("---start interactive with u...")
            # 赋一个变量 = [user]$:
            self.terminal_display = "[%s]$:"%self.user
            while True:
                # 显示的格式应该是 liang$:
                choice = input(self.terminal_display).strip()
                # 如果choice 直接敲回车就
                if len(choice) == 0:continue
                if choice=='q' and choice=='exit':exit("god bye")
                # 把输入的进行分割   比如  put filename
                cmd_list = choice.split()
                print(cmd_list )
                # 判断输入的 命令是否在 self 里面。就是类方法
                if hasattr(self,"_%s"%cmd_list[0]):
                    # 如果在就获取到内存地址
                    func = getattr(self,"_%s"%cmd_list[0])
                    # 执行这个内存地址，也就是这个类方法。传递一个参数，就是 put filename 传递过去
                    func(cmd_list)

                else:
                    print("Invalid cmd,type 'help' to check available commands. ")


    def __md5_required(self,cmd_list):
        '''检测命令是否需要进行MD5验证'''
        # 判断 '--md5'是否在cmd_list 中
        if '--md5' in cmd_list:
            return True


    def _help(self,*args,**kwargs):
        supported_actions = """
        get filename    #get file from FTP server
        put filename    #upload file to FTP server
        ls              #list files in current dir on FTP server
        pwd             #check current path on server
        cd path         #change directory , same usage as linux cd command
        touch           # touch file 
        rm              # rm file  rm director
        mkdir           # mkdir direcotr 
        """
        print(supported_actions)

    def show_progress(self,total):
        '''显示进度条 '''
        # 收到的大小
        received_size = 0
        # 现在的百分比
        current_percent = 0
        # 只要收到的大小，小于 原本的大小
        while received_size < total:
            # 计算百分比，要大于0
             if int((received_size / total) * 100 )   > current_percent :
                  print("#",end="",flush=True)
                  # 当前的百分比  收到的大小/ 总大小
                  current_percent = int((received_size / total) * 100 )
            # 这是一个... 迭代器
             new_size = yield
            # 加等于 new_size
             received_size += new_size

    def _cd(self,*args,**kwargs):
        #print("cd args",args)
        # args 是interactive 传递过来的值  cd .. 或者 cd test
        #  args[0] 就是 cd .. 或者cd test 所以要大于1
        if len(args[0]) >1:
            # 路径就是.. 或者 test
            path = args[0][1]
        else:
            # 如果 没有 就path 为空
            path = ''
        data = {'action': 'change_dir','path':path}
        # 把data 发送到服务端
        self.sock.send(json.dumps(data).encode())
        # 等待服务器接受
        response = self.get_response()
        # 如果接受的状态为260
        if response.get("status_code") == 260:
            #这个就是显示的路径  %s 就是这个用户的相对路径
            self.terminal_display ="%s:" % response.get('data').get("current_path")


    def _pwd(self,*args,**kwargs):
        # data 为一个字典
        data = {'action':'pwd'}
        # 发送一个data到服务端
        self.sock.send(json.dumps(data).encode())
        # 等待服务器的等待
        response = self.get_response()
        # 定义一个False
        has_err = False
        # 判断返回的状态码
        if response.get("status_code") == 200:
            #data 就是 显示当前用户的相对路径
            data = response.get("data")

            if data:
                print(data)
            else:
                has_err = True
        else:
            has_err = True

        if has_err:
            print("Error:something wrong.")

    def _ls(self,*args,**kwargs):
        #data 为 listdir
        data = {'action':'listdir'}
        # 发送给服务器端
        self.sock.send(json.dumps(data).encode())
        # 接受服务器的数据
        response = self.get_response()
        has_err = False
        # 如果状态码为200
        if response.get("status_code") == 200:
            # 那么data就为当前目录下的所有文件
            data = response.get("data")

            if data:
                print(data[1])
            else:
                has_err = True
        else:
            has_err = True

        if has_err:
            print("Error:something wrong.")

    def get_abs_path(self, *args, **kwargs):
        '''
        获取当前目录绝对路径
        :return:
        '''
        # 获取当前的绝对路径
        abs_path = os.getcwd()
        # 返回绝对路径
        return abs_path

    def _put(self, cmd_list):
        '''
        客户端上传文件
        :param args:
        :param kwargs:
        :return:
        '''
        # 就是接受的 put  filename
        if len(cmd_list) == 1:  # 需要接文件名
            print("No filename follows.")
            return


        #获取当前绝对路径
        abs_path = self.get_abs_path()
        # 获取到 filenam 是否与/ 开头
        if cmd_list[1].startswith("/"):
            # 如果是/user/aaa/aa 的方式就把 file 路径指定为这个
            file_abs_path = cmd_list[1]
        else:
            # 如果是直接的 filename 那么说明是在现在所处的位置的文件
            # 就是程序启动的位置的目录。相当于  当前的绝对路径+ 文件名 也就是cmd_list[1]
            file_abs_path = "{}/{}".format(abs_path, cmd_list[1])
        # 打印文件的绝对路径
        print("File abs path", file_abs_path)

        # 文件不存在时
        if not os.path.isfile(file_abs_path):
            print(STATUS_CODE[260])
            return

        # 提取文件名
        # 文件名一定是 输入的最后一个参数
        base_filename = cmd_list[1].split('/')[-1]
        # 发送数据到服务端
        data_header = {
            'action': 'put',
            'filename': base_filename
        }

        # 是否md5验证
        if self.__md5_required(cmd_list):
            data_header['md5'] = True
        # 发送过去
        self.sock.send(json.dumps(data_header).encode())
        # 接受服务器的相应
        response = self.get_response()

        # 如果状态码为288 就可以发送文件了
        if response["status_code"] == 288:  # 服务端准备接收文件
            print("---- ready to send file ----")
            # 打开这个文件
            file_obj = open(file_abs_path, "rb")
            # 获取到这个文件的大小
            file_size = os.path.getsize(file_abs_path)
            # 发送文件大小给服务器
            self.sock.send(json.dumps({'file_size': file_size}).encode())
            # 等待服务器 的回复
            self.sock.recv(1)  # 等待客户端确认
            # 如果有md5 的方式
            if data_header.get('md5'):
                md5_obj = hashlib.md5()
                for line in file_obj:
                    # 发送每一行就添加一个md5
                    self.sock.send(line)
                    md5_obj.update(line)
                else:
                    #发送完成之后呢 关闭文件
                    file_obj.close()

                    self.sock.recv(1)  # 解决粘包
                    print(STATUS_CODE[258])
                    # md5 的数字
                    md5_val = md5_obj.hexdigest()
                    # 发送md5 给服务端
                    self.sock.send(json.dumps({'md5': md5_val}).encode())
                    #等待服务端的回复
                    md5_response = self.get_response()
                    #如果回复中的状态码为267
                    if md5_response['status_code'] == 267:
                        # 那么就打印出 file 名字和状态码
                        print("[%s] %s!" % (base_filename, STATUS_CODE[267]))
                    else:
                        print("[%s] %s!" % (base_filename, STATUS_CODE[268]))
                    print("Send file done.")
            # 如果没有加入md5
            else:
                # 就直接发送给服务器
                for line in file_obj:
                    self.sock.send(line)
                else:
                    # 发送成功之后就关闭文件 。打印一个发送成功的标记
                    file_obj.close()
                    print("Send file done.")
        # 出现错误
        else:
            print(STATUS_CODE[256])
    def _put2(self,cmd_list):
        print("put--",cmd_list)
        if len(cmd_list)==1:
            print("请输入正确的文件")
            return
        filename=cmd_list[-1]
        print(filename)
        if os.path.isfile(filename):
            file_size=os.path.getsize(filename)
            data_header={
                'action':'put',
                'filename':filename,
                'filesize':file_size,
            }
            # if self.__md5_required(cmd_list):
            #     data_header['md5'] = True
            print("准备发送文件了")
            self.sock.send(json.dumps(data_header).encode())
            response = self.get_response()
            print("接受服务端相应")
            print(response)
            if response["status_code"] == 288:
                print("aa")
                received_size = 0
                received_data=b''
                print(file_size)
                while  received_size < file_size:
                    f=open(filename,"rb")
                    for line in f:
                        self.sock.send(line)
                        received_size+=len(line)
                        received_data+=line
                    else:
                        print("OK")
                        f.close()
        else:
            print("not is exists")

    def _get(self,cmd_list):
        #
        print("get--",cmd_list)
        # cmd_list 是一个列表 ['get','filename']
        if len(cmd_list) == 1:
            print("no filename follows...")
            return
        data_header = {
            'action':'get',
            'filename':cmd_list[1]
        }
        # 是否开启md5
        if self.__md5_required(cmd_list):
            # 添加一个md5标识给 data
            data_header['md5'] = True
        #发送data 给服务器
        self.sock.send(json.dumps(data_header).encode())
        # 接受服务器的标识
        response = self.get_response()
        print(response)
        # 如果状态码为257
        if response["status_code"] == 257:#ready to receive
            # 就发送一个1 给服务器。防止粘包
            self.sock.send(b'1')#send confirmation to server
            # 取出文件名
            base_filename = cmd_list[1].split('/')[-1]
            #收到的文件大小
            received_size = 0
            # 新建一个这个文件
            file_obj = open(base_filename,"wb")
            # 如果接受的size为0 就关闭吧。那还玩个毛线啊
            if response['data']['file_size'] == 0:
                file_obj.close()
                return
            # md5的方式 吧cmd_list 丢到md5 函数中
            if self.__md5_required(cmd_list):
                # 新建一个md5对象
                md5_obj = hashlib.md5()
                #显示进度条 传的一个值为 文件的大小
                progress = self.show_progress(response['data']['file_size']) #generator
                # 触发一下迭代器
                progress.__next__()
                # 接受到的大小 小于 总大小
                while received_size < response['data']['file_size']:
                    # 就一直收
                    data = self.sock.recv(4096)
                    # 收到的大小 +=data的长度
                    received_size += len(data)
                    try:
                        # 一直发送data 的长度
                      progress.send(len(data))
                    except StopIteration as e:
                      #如果出现报错就说明已经结束了
                      print("100%")
                    # 写入文件中
                    file_obj.write(data)
                    # 更新md5
                    md5_obj.update(data)
                else:
                    # 接受完之后呢打印一下接收完成
                    print("----->file recv done----")
                    # 关闭文件
                    file_obj.close()
                    # 打印一下md5 的值
                    md5_val = md5_obj.hexdigest()
                    # 接受服务器的响应
                    md5_from_server = self.get_response()
                    # 如果接受到的响应的状态码为258
                    if md5_from_server['status_code'] == 258:
                        #判断md5 是否一致
                        if md5_from_server['md5'] == md5_val:
                            print("%s 文件一致性校验成功!" % base_filename)
                    #print(md5_val,md5_from_server)

            else:
                # 如果不使用md5
                # 打印进度条
                progress = self.show_progress(response['data']['file_size']) #generator
                # 触发
                progress.__next__()
                # 接收到的文件 小于 get的文件大小
                while received_size < response['data']['file_size']:

                    # 接收
                    data = self.sock.recv(4096)
                    #
                    received_size += len(data)
                    file_obj.write(data)
                    try:
                        # 发送 给 迭代器
                      progress.send(len(data))
                    except StopIteration as e:
                      print("100%")


                else:
                    print("----->file rece done----")
                    file_obj.close()

    def _mkdir(self,cmd_list):
        print("-- mkdir",cmd_list)
        if len(cmd_list) == 1:
            print("no filename follows...")
            return
        data_header = {
            'action':'mkdir',
            'filename':cmd_list[1]
        }
        self.sock.send(json.dumps(data_header).encode())
        response = self.get_response()
        if response["status_code"] == 300:
            print("OK")
        else:
            print("NO")
    def _touch(self,cmd_list):
        print("-- touch",cmd_list)
        if len(cmd_list) == 1:
            print("no filename follows...")
            return
        data_header = {
            'action':'touch',
            'filename':cmd_list[1]
        }
        self.sock.send(json.dumps(data_header).encode())
        response = self.get_response()
        if response["status_code"] == 300:
            print("OK")
        else:
            print("NO")



    def _rm(self,cmd_list):
        print("-- touch",cmd_list)
        if len(cmd_list) == 1:
            print("no filename follows...")
            return
        data_header = {
            'action':'rm',
            'filename':cmd_list[1],
        }
        self.sock.send(json.dumps(data_header).encode())
        response = self.get_response()
        if response["status_code"] == 300:
            print("OK")
        else:
            print("NO")




if __name__ == "__main__":
    ftp = FTPClient()
    ftp.interactive() #交互
