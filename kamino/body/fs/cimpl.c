
// Compile with:
//
// gcc -shared -Wl,-soname,libstatwrap.so.1 -o libstatwrap.so.1.0 -fPIC t2.c

#include <sys/types.h>
#include <sys/stat.h>
#include <sys/vfs.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <fcntl.h>

struct tspec {
   long sec;
   long nsec;
};

struct sdev {
   long major;
   long minor;
};

struct swrap {
   unsigned long long dev;
   unsigned long long ino;
   unsigned int mode;
   unsigned long long nlink;
   unsigned long uid;
   unsigned long gid;
   struct sdev rdev;
   unsigned long long size;
   unsigned long long blksize;
   unsigned long long blocks;
   struct tspec atime;
   struct tspec mtime;
   struct tspec ctime;
};

int statwrap( const char * path, struct swrap * w )
{
   struct stat s;

   if ( lstat(path, &s) < 0 )
      return -1;

   w->dev = s.st_dev;
   w->ino = s.st_ino;
   w->mode = s.st_mode;
   w->nlink = s.st_nlink;
   w->uid   = s.st_uid;
   w->gid   = s.st_gid;
   w->rdev.major  = major(s.st_rdev);
   w->rdev.minor  = minor(s.st_rdev);
   w->size  = s.st_size;
   w->blksize = s.st_blksize;
   w->blocks  = s.st_blocks;
   w->atime.sec = s.st_atim.tv_sec;
   w->atime.nsec = s.st_atim.tv_nsec;

   w->mtime.sec = s.st_mtim.tv_sec;
   w->mtime.nsec = s.st_mtim.tv_nsec;

   w->ctime.sec = s.st_ctim.tv_sec;
   w->ctime.nsec = s.st_ctim.tv_nsec;

   return 0;
}


int set_mtime_ns( const char * abs_filename, long sec, long nsec )
{
   struct timespec ts[2];

   ts[0].tv_sec  = sec;
   ts[0].tv_nsec = nsec;
   ts[1].tv_sec  = sec;
   ts[1].tv_nsec = nsec;
   
   return utimensat(0, abs_filename, ts, AT_SYMLINK_NOFOLLOW);
}


