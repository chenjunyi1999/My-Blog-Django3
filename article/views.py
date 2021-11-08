import markdown
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect

from comment.models import Comment
from .forms import ArticlePostForm
from comment.forms import CommentForm
from .models import ArtcilePost, ArticleColumn


# def article_list(request):
#     search = request.GET.get('search')
#     order = request.GET.get('order')
#     column = request.GET.get('column')
#     tag =request.GET.get('tag')
#     # 用户搜索逻辑
#     if search:
#         if order == 'total_views':
#             # 用 Q对象 进行联合搜索
#             article_list = ArtcilePost.objects.filter(
#                 Q(title__icontains=search) | Q(body__icontains=search)
#             ).order_by('-total_views')
#         else:
#             article_list = ArtcilePost.objects.filter(
#                 Q(title__icontains=search) | Q(body__icontains=search)
#             )
#     else:
#         # 将 search 参数重置为空
#         search = ''
#         if order == 'total_views':
#             article_list = ArtcilePost.objects.all().order_by('-total_views')
#         else:
#             article_list = ArtcilePost.objects.all()
#
#     paginator = Paginator(article_list, 3)
#     page = request.GET.get('page')
#     articles = paginator.get_page(page)
#
#     # 增加 search 到 context
#     context = { 'articles': articles, 'order': order, 'search': search }
#
#     return render(request, 'article/list.html', context)


def article_list(request):
    # 从 url 中提取查询参数
    search = request.GET.get('search')
    order = request.GET.get('order')
    column = request.GET.get('column')
    tag = request.GET.get('tag')

    # 初始化查询集
    article_list = ArtcilePost.objects.all()

    # 搜索查询集
    if search:
        article_list = article_list.filter(
            Q(title__icontains=search) |
            Q(body__icontains=search)
        )
    else:
        search = ''

    # 栏目查询集
    if column is not None and column.isdigit():
        article_list = article_list.filter(column=column)

    # 标签查询集
    if tag and tag != 'None':
        article_list = article_list.filter(tags__name__in=[tag])

    # 查询集排序
    if order == 'total_views':
        article_list = article_list.order_by('-total_views')

    paginator = Paginator(article_list, 3)
    page = request.GET.get('page')
    articles = paginator.get_page(page)

    # 需要传递给模板（templates）的对象
    context = {
        'articles': articles,
        'order': order,
        'search': search,
        'column': column,
        'tag': tag,
    }

    return render(request, 'article/list.html', context)


def article_detail(request, id):
    article = ArtcilePost.objects.get(id=id)

    article.total_views += 1
    article.save(update_fields=['total_views'])
    comments = Comment.objects.filter(article=id)
    # 将markdown语法渲染成html样式
    md = markdown.Markdown(
        extensions=[
            # 包含 缩写、表格等常用扩展
            'markdown.extensions.extra',
            # 语法高亮扩展
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
        ])
    article.body = md.convert(article.body)
    comment_form = CommentForm()
    context = {'article': article, 'toc': md.toc, 'comments': comments,'comment_form': comment_form,}
    return render(request, 'article/detail.html', context)


@login_required(login_url='/userprofile/login/')
def article_create(request):
    if request.method == "POST":
        article_post_form = ArticlePostForm(request.POST, request.FILES)
        if article_post_form.is_valid():
            new_article = article_post_form.save(commit=False)
            # new_article.author = User.objects.get(id = 1)
            new_article.author = User.objects.get(id=request.user.id)

            if request.POST['column'] != 'none':
                new_article.column = ArticleColumn.objects.get(id=request.POST['column'])

            new_article.save()
            article_post_form.save_m2m()
            return redirect("article:article_list")
        else:
            return HttpResponse("输入错误")
    else:
        article_post_form = ArticlePostForm()

        columns = ArticleColumn.objects.all()
        context = {'article_post_form': article_post_form, 'columns': columns}
        return render(request, 'article/create.html', context)


@login_required(login_url='/userprofile/login/')
def article_safe_delete(request, id):
    article = ArtcilePost.objects.get(id=id)
    if request.user != article.author:
        return HttpResponse("抱歉，你无权删除这篇文章。")
    if request.method == "POST":
        article = ArtcilePost.objects.get(id=id)
        article.delete()
        return redirect("article:article_list")
    else:
        return HttpResponse("仅允许post请求")


@login_required(login_url='/userprofile/login/')
def article_update(request, id):
    """
    更新文章的视图函数
    通过POST方法提交表单，更新titile、body字段
    GET方法进入初始表单页面
    id： 文章的 id
    """
    article = ArtcilePost.objects.get(id=id)
    if request.user != article.author:
        return HttpResponse("抱歉，你无权修改这篇文章。")
    if request.method == 'POST':
        article_post_form = ArticlePostForm(data=request.POST)
        if article_post_form.is_valid():
            article.title = request.POST['title']
            article.body = request.POST['body']
            # 新增的代码
            if request.POST['column'] != 'none':
                article.column = ArticleColumn.objects.get(id=request.POST['column'])
            else:
                article.column = None

            if request.FILES.get('avatar'):
                article.avatar = request.FILES.get('avatar')

            article.tags.set(*request.POST.get('tags').split(','), clear=True)
            article.save()

            return redirect("article:article_detail", id=id)
        else:
            return HttpResponse("表单错误")
    else:
        # 创建表单类实例
        article_post_form = ArticlePostForm()

        columns = ArticleColumn.objects.all()
        # 赋值上下文，将 article 文章对象也传递进去，以便提取旧的内容
        context = {'article': article, 'article_post_form': article_post_form, 'columns': columns,'tags': ','.join([x for x in article.tags.names()]),}
        # 将响应返回到模板中
        return render(request, 'article/update.html', context)



