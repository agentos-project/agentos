# Git alias
alias gga='git add'
alias ggp='git push origin `git rev-parse --abbrev-ref HEAD`'
alias ggl='git log --graph --pretty=format:"%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset" --abbrev-commit'
alias ggf='git fetch'
alias ggs='git status'
alias ggd='git diff'
alias ggm='git commit -m'
alias ggma='git commit -am'
alias ggb='git branch'
alias ggc='git checkout'
alias ggra='git remote add'
alias ggra='git remote add'
alias ggr='git rebase'
alias ggpur='git pull --rebase'
alias ggpun='git pull'
alias ggcl='git clone'

# Working aliases
alias sdf='cd ~/200words'

# Bash options
shopt -s histappend
export HISTIGNORE="ignoredups:&:ls:[bf]g:exit"
export HISTSIZE=100000
export HISTFILESIZE=200000
set -o vi
shopt -s checkwinsize
PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '

# Environment
export PATH=$HOME/Library/Python/2.7/bin/:/Library/Frameworks/Python.framework/Versions/2.7/bin:/usr/local/opt/ruby/bin:$HOME/.gem/ruby/2.7.0/bin:$PATH
export PGDATA=~/.pgdata

# OS X stops complaining about zsh
export BASH_SILENCE_DEPRECATION_WARNING=1

# Virtual env
export WORKON_HOME=$HOME/.virtualenvs/
export VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python3
if [ ! -e $HOME/.virtualenvs ]; then
    mkdir -p $HOME/.virtualenvs
fi
if [ -e /usr/local/bin/virtualenvwrapper.sh ]; then
    source /usr/local/bin/virtualenvwrapper.sh
elif [ -e /usr/bin/virtualenvwrapper.sh ]; then
    source /usr/bin/virtualenvwrapper.sh
fi

# Python startup
export PYTHONSTARTUP=$HOME/.pystartup
if [ ! -e $PYTHONSTARTUP ]; then
    echo "import atexit" > $PYTHONSTARTUP
    echo "import os" >> $PYTHONSTARTUP
    echo "import readline" >> $PYTHONSTARTUP
    echo "import rlcompleter" >> $PYTHONSTARTUP
    echo "import sys" >> $PYTHONSTARTUP
    echo "hist = os.path.join(os.environ['HOME'], '.pyhist')" >> $PYTHONSTARTUP
    echo "try:" >> $PYTHONSTARTUP
    echo "    readline.read_history_file(hist)" >> $PYTHONSTARTUP
    echo "except IOError:" >> $PYTHONSTARTUP
    echo "    pass" >> $PYTHONSTARTUP
    echo "readline.parse_and_bind('set editing-mode vi')" >> $PYTHONSTARTUP
    echo "atexit.register(readline.write_history_file, hist)" >> $PYTHONSTARTUP
    echo "del os, hist" >> $PYTHONSTARTUP
fi

if [ ! -e $HOME/.vimrc ]; then
    mkdir -p $HOME/.vimtmp
    echo "set nocompatible" > $HOME/.vimrc
    echo "set backspace=indent,eol,start" >> $HOME/.vimrc
    echo "set expandtab" >> $HOME/.vimrc
    echo "set shiftwidth=4" >> $HOME/.vimrc
    echo "set tabstop=4" >> $HOME/.vimrc
    echo "set smarttab" >> $HOME/.vimrc
    echo "set smartindent" >> $HOME/.vimrc
    echo "set autochdir" >> $HOME/.vimrc
    echo "set background=dark" >> $HOME/.vimrc
    echo "set history=50 " >> $HOME/.vimrc
    echo "set ruler" >> $HOME/.vimrc
    echo "set showcmd" >> $HOME/.vimrc
    echo "set incsearch" >> $HOME/.vimrc
    echo "set nobackup nowritebackup" >> $HOME/.vimrc
    echo "set dir=>~/.vimtmp" >> $HOME/.vimrc
    echo "set hlsearch" >> $HOME/.vimrc
    echo "syntax enable" >> $HOME/.vimrc
    echo "filetype indent plugin on" >> $HOME/.vimrc
    # Custom per-language vim settings
    mkdir -p $HOME/.vim/ftplugin
    # Custom JS settings (mostly indent size)
    echo "set expandtab" >> $HOME/.vim/ftplugin/javascript.vim
    echo "set shiftwidth=2" >> $HOME/.vim/ftplugin/javascript.vim
    echo "set tabstop=2" >> $HOME/.vim/ftplugin/javascript.vim
    echo "set smarttab" >> $HOME/.vim/ftplugin/javascript.vim
    echo "set smartindent" >> $HOME/.vim/ftplugin/javascript.vim
    echo "syntax enable" >> $HOME/.vim/ftplugin/javascript.vim
    # Ubuntu on Windows Terminal specific settings
    echo "If you're using Windows Terminal, enable the commented out settings in ~/.vimrc"
    echo "" >> $HOME/.vimrc
    echo "\" Uncomment below for Windows Terminal settings" >> $HOME/.vimrc
    echo "\" Other Windows Terminal changes in its settings.json:" >> $HOME/.vimrc
    echo "\"   * \"colorScheme\": \"Tango Dark\" (in Ubuntu profile)" >> $HOME/.vimrc
    echo "\"   * \"cursorShape\": \"filledBox\" (in Ubuntu profile)" >> $HOME/.vimrc
    echo "\"   * Comment out copy ctrl+c binding in \"actions\" (ctrl+shift+c will work)" >> $HOME/.vimrc
    echo "\"   * Comment out paste ctrl+v binding in \"actions\" so it doesn't interfere with visual block (ctrl+shift+v will work)" >> $HOME/.vimrc
    echo "" >> $HOME/.vimrc
    echo "\" let &t_SI = \"\\e[6 q\"" >> $HOME/.vimrc
    echo "\" let &t_SR = \"\\e[3 q\"" >> $HOME/.vimrc
    echo "\" let &t_EI = \"\\e[2 q\"" >> $HOME/.vimrc
    echo "" >> $HOME/.vimrc
    echo "\" augroup myCmds" >> $HOME/.vimrc
    echo "\" au!" >> $HOME/.vimrc
    echo "\" autocmd VimEnter * silent !echo -ne \"\\e[2 q\"" >> $HOME/.vimrc
    echo "\" augroup END" >> $HOME/.vimrc
fi

# Vi key bindings etc
if [ ! -e $HOME/.editrc ]; then
    echo "bind -v" > $HOME/.editrc
fi

if [ ! -e $HOME/.inputrc ]; then
    echo "set editing-mode vi" > $HOME/.inputrc
fi

if [ ! -e $HOME/.gitconfig ]; then
    git config --global user.name "Nick Jalbert"
    git config --global user.email "nick@jalbert.io"
    git config --global core.editor "/usr/bin/vim"
    # https://github.com/so-fancy/diff-so-fancy
    git config --global core.pager "diff-so-fancy | less --tabs=4 -RFX"
    git config --global color.ui true
    git config --global color.diff-highlight.oldNormal "red bold"
    git config --global color.diff-highlight.oldHighlight "red bold 52"
    git config --global color.diff-highlight.newNormal "green bold"
    git config --global color.diff-highlight.newHighlight "green bold 22"
    git config --global color.diff.meta "227"
    git config --global color.diff.frag "magenta bold"
    git config --global color.diff.commit "227 bold"
    git config --global color.diff.old "red bold"
    git config --global color.diff.new "green bold"
    git config --global color.diff.whitespace "red reverse"
    git config --bool --global diff-so-fancy.changeHunkIndicators true
    git config --bool --global diff-so-fancy.stripLeadingSymbols true
fi

cd ~
