include ChefUtils::Account

action :create do
  user = new_resource.name
  groups = new_resource.groups
  key_source = new_resource.key_source
  akf = new_resource.authorized_keys_for


  homedir = if new_resource.homedir == nil
              node[:etc][:passwd][user][:dir] rescue "/var/app/#{user}"
            else
              new_resource.homedir
            end

  group user

  account user do
    comment user
    home homedir
    home_mode "0755"
    gid user
    groups groups
    authorized_keys_for akf if akf
    key_source key_source if key_source
  end

  %w(
    bin
    releases
    shared
  ).each do |d|
    directory "#{homedir}/#{d}" do
      owner user
      group user
      mode "0755"
    end
  end

  shared = %w(config log pids system) + new_resource.shared

  shared.uniq.each do |d|
    directory "#{homedir}/shared/#{d}" do
      owner user
      group user
      mode "0755"
    end
  end

  splunk_input "monitor://#{homedir}/shared/log/*.log"

  file "/etc/logrotate.d/deploy-#{user}" do
    content <<-EOS
#{homedir}/shared/log/*.log {
 missingok
 rotate 21
 copytruncate
}
EOS
    owner "root"
    group "root"
    mode "0644"
  end

end
