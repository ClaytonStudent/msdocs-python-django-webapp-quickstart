from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

def index(request):
    print('Request for index page received')
    return render(request, 'hello_azure/stock_value_report.html')

@csrf_exempt
def hello(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        
        if name is None or name == '':
            print("Request for hello page received with no name or blank name -- redirecting")
            return redirect('index')
        else:
            print("Request for hello page received with name=%s" % name)
            context = {'name': name }
            return render(request, 'hello_azure/hello.html', context)
    else:
        return redirect('index')
    

from django.shortcuts import render
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
import os
from django.conf import settings
import pandas as pd
from django.http import FileResponse

def home(request):
    context = {"data":"Home Page of HDGROUP"}
    return render(request,'hello_azure/home.html', context)

'''
1. Stock Value Report
'''
@csrf_exempt
def stock_value_report(request):
    if request.method == 'POST':
        try:
            # Check if files were uploaded
            if 'myfile1' not in request.FILES and 'myfile2' not in request.FILES:
                return render(request, 'hello_azure/stock_value_report.html', {
                    'error': '请上传所需的文件：产品导出文件和库存文件'
                })
            elif 'myfile1' not in request.FILES:
                return render(request, 'hello_azure/stock_value_report.html', {
                    'error': '请上传产品导出文件（博讯 - 销售 - 详细查询 - 产品批量操作 - 产品导出）'
                })
            elif 'myfile2' not in request.FILES:
                return render(request, 'hello_azure/stock_value_report.html', {
                    'error': '请上传库存文件（博讯 - 销售 - 详细查询 - 库存）'
                })
            
            myfile1 = request.FILES['myfile1']
            myfile2 = request.FILES['myfile2']
            
            # Check if files are empty
            if not myfile1.name or not myfile2.name:
                return render(request, 'hello_azure/stock_value_report.html', {
                    'error': '请选择有效的文件，文件名不能为空'
                })
            
            # Check file extensions
            if not myfile1.name.endswith('.csv'):
                return render(request, 'hello_azure/stock_value_report.html', {
                    'error': '产品导出文件必须是CSV格式'
                })
            if not (myfile2.name.endswith('.xlsx') or myfile2.name.endswith('.xls')):
                return render(request, 'hello_azure/stock_value_report.html', {
                    'error': '库存文件必须是Excel格式(.xlsx或.xls)'
                })
            
            fs = FileSystemStorage()
            if fs.exists(myfile1.name):
                fs.delete(myfile1.name)
            if fs.exists(myfile2.name):
                fs.delete(myfile2.name)
            
            filename1 = fs.save(myfile1.name, myfile1)
            filename2 = fs.save(myfile2.name, myfile2)
            
            try:
                data = analysis_stock_value_report(filename1, filename2) #{'stock_value_without_iva':100,'stock_value':1} #
                return render(request, 'hello_azure/stock_value_report.html', {'data': data})
            except pd.errors.EmptyDataError:
                return render(request, 'hello_azure/stock_value_report.html', {
                    'error': '上传的文件内容为空，请确保文件包含有效数据'
                })
            except Exception as e:
                return render(request, 'hello_azure/stock_value_report.html', {
                    'error': f'处理文件时出错：{str(e)}'
                })
            
        except Exception as e:
            return render(request, 'hello_azure/stock_value_report.html', {
                'error': '系统错误，请稍后重试或联系管理员'
            })
            
    return render(request, 'hello_azure/stock_value_report.html')
def analysis_stock_value_report(filename1,filename2):
    file1 = os.path.join(settings.MEDIA_ROOT, filename1)
    file2 = os.path.join(settings.MEDIA_ROOT, filename2)
    df_product = get_product(file1)
    df_stock = pd.read_html(file2)[0]
    df_stock = get_stock(df_stock)
    merged_df,tax_counts = get_merged_df(df_stock,df_product)
    stock_value,stock_value_without_iva = get_stock_value(merged_df)
    data = {
        "date": filename2.split('_')[2],
        "stock_value": stock_value,
        "stock_value_without_iva": stock_value_without_iva,
        "sale_tax_rate_counts": tax_counts
    }
    # Specify the path to the text file
    file_name = "StockValue.txt"  # Replace with your desired file path
    file_path = os.path.join(settings.MEDIA_ROOT, file_name)
    # Open the file for writing
    with open(file_path, 'w') as file:
        # Write the data to the file
        for key, value in data.items():
            file.write(f"{key}: {value}\n")
    file.close()
    return data 
def get_product(product_file):
    df_product = pd.read_csv(product_file)
    df_product.drop(df_product.tail(1).index,inplace=True)
    df_product = df_product[df_product['valid_grade']>=1]
    df_product = df_product[['product_model','product_description','stockpile_quantity','sale_tax_rate','stock_price']]
    return df_product
def get_stock(df):
    #df = pd.read_html(stock_file)[0]
    # drop the last 1 rows
    df.drop(df.tail(1).index,inplace=True)
    # drop the name empty product
    df = df[~df['品名'].isna()]
    # drop the under 0 stock
    df = df[df['主仓库库存']>0]
    # drop LOOK OCCHIALI EXPO
    df_expo = df[df.品名.str.contains("LOOK OCCHIALI EXPO")]
    df.drop(df_expo.index,inplace=True)
    # Drop one item
    condition = df['型号'] == '30IOI0000002000'
    df = df[~condition]
    #out_index = df.index[df['型号'] == '30IOI0000002000'].to_list()[0]
    #df.drop(index=out_index,inplace=True)
    # rename the columns
    df.rename(columns={'型号':'product_model'}, inplace=True)
    return df
def get_merged_df(df_stock,df_product):
    merged_df = df_stock.merge(df_product, on='product_model', how='left')
    tax_counts = merged_df['sale_tax_rate'].value_counts(dropna=False).to_dict()
    merged_df['sale_tax_rate'].fillna(0, inplace=True)
    merged_df['sale_tax_rate'] = (merged_df['sale_tax_rate'] + 100) / 100
    return merged_df,tax_counts
def get_stock_value(merged_df):
    avg_stock = sum(merged_df[merged_df['成本小计']>0]['成本小计'] * merged_df[merged_df['成本小计']>0]['sale_tax_rate'])
    remain_stock = sum(merged_df[merged_df['成本小计']<=0]['小计'] * merged_df[merged_df['成本小计']<=0]['sale_tax_rate'])
    stock_value = avg_stock + remain_stock
    stock_value_without_iva = merged_df['小计'].sum()
    return int(stock_value), int(stock_value_without_iva)
def download_file(request):
    source = request.GET.get('source', None)
    file_path = os.path.join(settings.MEDIA_ROOT, source)
    file = open(file_path, 'rb')
    response = FileResponse(file)
    response['Content-Disposition'] = f'attachment; filename="{source}"'
    return response