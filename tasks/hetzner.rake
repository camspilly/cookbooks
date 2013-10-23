# remote commands for maintenance

require 'ap'
require 'irb'
require 'ripl'

class HetznerConsole
  def initialize
    Ripl.start(binding: binding)
  end

  def method_missing(name, *args, &block)
    if hetzner.respond_to?(name)
      hetzner.send(name, *args, &block)
    else
      super
    end
  end
end

namespace :hetzner do

  desc "open hetzner console"
  task :console do |t, args|
    HetznerConsole.new
  end

  desc "reset machine via Hetzner Robot"
  task :reset, :fqdn do |t, args|
    search("fqdn:#{args.fqdn}") do |node|
      hetzner.reset!(node[:primary_ipaddress], :hw)
      wait_for_ssh(node[:fqdn])
    end
  end

  desc "enable rescue and rebootstrap"
  task :reinstall, :fqdn, :profile do |t, args|
    args.with_defaults(:profile => 'generic-two-disk-md')
    search("fqdn:#{args.fqdn}") do |node|
      res = hetzner.enable_rescue!(node[:primary_ipaddress], 'linux', '64')
      password = res.parsed_response["rescue"]["password"]
      puts "rescue password is #{password.inspect}"
      hetzner.reset!(node[:primary_ipaddress], :hw)
      wait_for_ssh(node[:fqdn])
      Rake::Task['node:quickstart'].invoke(node[:fqdn], node[:primary_ipaddress], password, args.profile)
    end
  end

  desc "Set server names and reverse DNS"
  task :dns do
    search("*:*") do |node|
      fqdn = node[:fqdn]
      name = fqdn.sub(/\.#{node[:chef_domain]}$/, '')
      ip = Resolv.getaddress(fqdn)

      if ip != node[:primary_ipaddress]
        puts "IP #{node[:primary_ipaddress]} does not match resolved address #{ip} for FQDN #{fqdn}"
      end

      hetzner_server_name_rdns(ip, name, fqdn)
    end
  end

end
