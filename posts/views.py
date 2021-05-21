from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator

from .models import Post, Group, PostForm, User, CommentForm, Follow
import datetime as dt


def index(request):
    # одна строка вместо тысячи слов на SQL
    post_all = Post.objects.order_by('-pub_date').all()
    paginator = Paginator(post_all, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    # собираем тексты постов в один, разделяя новой строкой
    return render(request, "index.html", {"page": page, "paginator": paginator})


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = Post.objects.filter(group=group).order_by('-pub_date').all()
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, "group.html", {"page": page, "group": group, "paginator": paginator})


@login_required
def new_post(request):
    context = {'title': 'Новый пост',
               'button': 'Добавить'}
    if request.method == 'POST':
        form = PostForm(request.POST)

        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.pub_date = dt.datetime.now()
            post.save()
            return redirect('index')
        return render(request, 'new.html', {'form': form, 'context': context})
    form = PostForm()
    return render(request, 'new.html', {'form': form, 'context': context})


def profile(request, username):
    prof_user = get_object_or_404(User, username=username)
    post_author = Post.objects.filter(author=prof_user).order_by('-pub_date').all()
    following = User.objects.get(id=request.user.id).follower.filter(author=prof_user)
    count_fol = User.objects.get(id=prof_user.id)
    paginator = Paginator(post_author, 10)
    count = paginator.count
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)

    return render(request, 'profile.html',
                  {'prof_user': prof_user, 'post_author': post_author, 'page': page, 'count': count,
                   'paginator': paginator, 'following': following, 'count_fol': count_fol})


def post_view(request, username, post_id):
    prof_user = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, author__username=prof_user, id=post_id)
    count = len(Post.objects.filter(author=prof_user).all())
    items = post.comments.all()
    if request.method == 'GET':
        form = CommentForm()
        return render(request, 'post.html',
                      {'form': form, 'post': post, 'items': items, 'prof_user': prof_user, 'count': count})


# return render(request, 'post.html', {'prof_user': prof_user, 'post': post, 'count': count, 'items': items})


@login_required
def post_edit(request, username, post_id):
    prof_user = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, author__username=username, id=post_id)
    if prof_user == request.user:
        context = {'title': 'Редактировать запись',
                   'button': 'Сохранить'}
        form = PostForm(request.POST or None, files=request.FILES or None, instance=post)
        if request.method == 'POST':
            if form.is_valid():
                post = form.save(commit=False)  # Это скорее всего не нужно
                post.save()
                return redirect(f'/{username}/{post_id}/')
        return render(request, 'new.html', {'form': form, 'context': context})

    return redirect(f'/{username}/{post_id}/')


@login_required
def add_comment(request, username, post_id):
    prof_user = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, author__username=prof_user, id=post_id)
    if request.method == 'POST':
        form = CommentForm(request.POST or None)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.created = dt.datetime.now()
            comment.save()
            return redirect(f'/{username}/{post_id}/')
        return render(request, 'post.html',
                      {'form': form, 'post': post})


@login_required
def follow_index(request):
    # информация о текущем пользователе доступна в переменной request.user
    user_follow = User.objects.get(id=request.user.id).follower.all().values_list('author')
    post_follow = Post.objects.filter(author__in=user_follow).order_by('-pub_date').all()
    paginator = Paginator(post_follow, 5)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    # собираем тексты постов в один, разделяя новой строкой
    return render(request, "follow.html", {"page": page, "paginator": paginator})


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect(f'/{username}/')


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        follower = Follow.objects.get(user=request.user, author=author)
        follower.delete()
    return redirect(f'/{username}/')


def page_not_found(request, exception):
    # Переменная exception содержит отладочную информацию,
    # выводить её в шаблон пользователской страницы 404 мы не станем
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)
