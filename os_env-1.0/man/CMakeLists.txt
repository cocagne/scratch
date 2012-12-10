cmake_minimum_required(VERSION 2.8)


install( FILES os_env.1 os_env_update.1 DESTINATION usr/share/man/man1 PERMISSIONS 
         OWNER_READ OWNER_WRITE GROUP_READ WORLD_READ )

install( FILES os_env.conf.5 DESTINATION usr/share/man/man5 PERMISSIONS 
         OWNER_READ OWNER_WRITE GROUP_READ WORLD_READ )



