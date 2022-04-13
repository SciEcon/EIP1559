#include<unordered_map>
#include<string>
#include<cstring>
#include<iostream>
#include<cstdio>
#include<cassert>
#define lim 10000100
using namespace std;
char st[lim+10],tmp[lim+10];
unordered_map <string,double> mp;
string next_hour(string st)
{
    //2021071501
    int days_per_month[13]={0,31,28,31,30,31,30,31,31,30,31,30,31};
    int year=atoi(st.substr(0,4).c_str());
    if (((year%4==0)&&(year%100!=0))||(year%400==0)) days_per_month[2]++;
    int month=atoi(st.substr(4,2).c_str());
    int day=atoi(st.substr(6,2).c_str());
    int hour=atoi(st.substr(8,2).c_str());
    if (hour<23){hour++;}
    else if (day<days_per_month[month]){hour=0;day++;}
    else if (month<12){hour=0;day=1;month++;}
    else{hour=0;day=1;month=1;year++;}
    char tmp[20];
    sprintf(tmp,"%04d%02d%02d%02d",year,month,day,hour);
    return string(tmp);
}
int main(int argc,char **argv)
{
    /*
    freopen("tmp.out","w",stdout);
    string ths="2020123100";
    for (int i=1;i<=366;i++)
    {
        for (int j=0;j<24;j++) ths=next_hour(ths);
        cout<<ths<<endl;
    }
    return 0;
    */


    if (argc!=4)
    {
        cerr<<"need three parameter: server from to";
        return 0;
    }
    string server=argv[1],tim_fr=argv[2],tim_to=argv[3];
    string cachefile="./cache/"+server+"_cache";
    for (string tim=tim_fr;tim!=tim_to;tim=next_hour(tim))
    {
        cerr<<"begin "<<tim<<endl;
        string path="/data/txstore/"+server+"/tx.log-"+tim+".gz";
        string command="ls -l "+path;
        if (system(command.c_str())!=0)
        {
            cerr<<path<<" not found"<<endl;
            continue;
        }
        command="gzip -cd "+path+" > "+cachefile;
        cerr<<command<<endl;
        if (system(command.c_str())!=0)
        {
            cerr<<path<<" is not a legal .gz file"<<endl;
            continue;
        }
        cerr<<"gzip end"<<endl;
        
        FILE *f=fopen(cachefile.c_str(),"r");
        while (fgets(st,lim,f))
        {
            st[lim]='\0';
            int len=strlen(st);
            if (len>lim-10) assert(0);
            if ((len<=2)||(st[0]!='{')||(st[len-1]!='}')) continue;
            //cerr<<st<<endl;
            int bg=int(strstr(st,"tx_hash")-st)+10;
                //cerr<<"bg "<<bg<<endl;
            int ed=strstr(st+bg,"\"")-st;
                //cerr<<"ed "<<ed<<endl;
            for (int i=bg;i<ed;i++) tmp[i-bg]=st[i];
            tmp[ed-bg]='\0';
            string hash=tmp;
            bg=int(strstr(st,"timeSeen")-st)+10;
                //cerr<<"bg "<<bg<<endl;
            ed=strstr(st+bg,",")-st;
                //cerr<<"ed "<<ed<<endl;
            for (int i=bg;i<ed;i++) tmp[i-bg]=st[i];
            tmp[ed-bg]='\0';
            double tim;sscanf(tmp,"%lf",&tim);
            unordered_map <string,double>::iterator it=mp.find(hash);
            if (it==mp.end()) mp[hash]=tim;
            else if (tim<it->second) mp[hash]=tim;
        }
    }
    sprintf(tmp,"./compressed/%s_[%s,%s)_compressed.txt",server.c_str(),tim_fr.c_str(),tim_to.c_str());
    freopen(tmp,"w",stdout);
    for (unordered_map <string,double>::iterator it=mp.begin();it!=mp.end();it++)
        printf("%s %.3f\n",it->first.c_str(),it->second);
}